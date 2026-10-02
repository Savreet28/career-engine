"""
embedder.py
===========

Turns text into a dense vector ("embedding") so that similarity can be
measured by direction rather than by shared keywords.

What an embedding is (viva answer)
----------------------------------
An embedding model maps a piece of text to a fixed-length list of numbers --
here 384 of them. The model is trained so that texts with similar *meaning*
land close together in that 384-dimensional space. This is why the query
"AI/ML Engineer" can retrieve a chunk that says "train deep learning models
with PyTorch" even though the two share no words.

All vectors produced here are L2-normalised (unit length). With unit vectors,
the dot product **is** the cosine similarity, so the vector store can use a
plain inner-product index and still be doing cosine search.

Two interchangeable backends
----------------------------
1. ``sentence-transformers`` with ``all-MiniLM-L6-v2`` -- a small, free,
   locally-run neural model (~90 MB, downloaded once). This is the default.
2. ``TF-IDF + Truncated SVD`` (Latent Semantic Analysis) -- pure scikit-learn,
   no download, no network. Used automatically if the neural model cannot be
   loaded, and selectable with ``FORCE_OFFLINE_EMBEDDINGS=1``.

Having a real fallback means the project always runs, and it gives a concrete
comparison point when explaining *why* neural embeddings are worth it.
"""

from __future__ import annotations

import logging
import threading
from typing import List, Optional, Sequence

import numpy as np

import config

logger = logging.getLogger("career_engine.rag.embedder")


class Embedder:
    """Common interface for both embedding backends."""

    backend: str = "base"
    name: str = "base"
    dimension: int = 0
    requires_fit: bool = False

    def fit(self, corpus: Sequence[str]) -> None:
        """Backends that learn from the corpus override this."""

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        raise NotImplementedError

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

    def describe(self) -> dict:
        return {
            "backend": self.backend,
            "model": self.name,
            "dimension": self.dimension,
            "normalised": True,
        }


def _l2_normalise(matrix: np.ndarray) -> np.ndarray:
    """Scale every row to unit length so dot product == cosine similarity."""
    matrix = np.asarray(matrix, dtype="float32")
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0          # avoid dividing an all-zero vector by zero
    return (matrix / norms).astype("float32")


class SentenceTransformerEmbedder(Embedder):
    """Neural sentence embeddings via sentence-transformers (runs locally)."""

    backend = "sentence-transformers"

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.name = model_name
        self._model = SentenceTransformer(model_name)
        # sentence-transformers renamed this method in v6; support both.
        get_dim = getattr(self._model, "get_embedding_dimension", None) or \
            self._model.get_sentence_embedding_dimension
        self.dimension = int(get_dim())

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype="float32")
        vectors = self._model.encode(
            list(texts),
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype="float32")


class TfidfSvdEmbedder(Embedder):
    """
    Offline fallback: TF-IDF term weighting reduced with Truncated SVD.

    This is classical Latent Semantic Analysis. It captures term co-occurrence
    rather than trained semantics, so it is weaker than the neural model on
    paraphrases -- but it needs no download, is fully deterministic, and keeps
    the whole RAG pipeline working offline.
    """

    backend = "tfidf-svd"
    requires_fit = True

    def __init__(self, n_components: int = 256):
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.name = f"tfidf+svd({n_components})"
        self._requested_components = n_components
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
        )
        self._svd: Optional[TruncatedSVD] = None
        self._TruncatedSVD = TruncatedSVD
        self._fitted = False

    def fit(self, corpus: Sequence[str]) -> None:
        corpus = [t for t in corpus if t and t.strip()]
        if not corpus:
            raise ValueError("Cannot fit the offline embedder on an empty corpus.")

        tfidf = self._vectorizer.fit_transform(corpus)
        # SVD components must stay below both the vocabulary size and the
        # number of documents, otherwise scikit-learn raises.
        n_components = max(2, min(self._requested_components,
                                  tfidf.shape[1] - 1, tfidf.shape[0] - 1))
        self._svd = self._TruncatedSVD(n_components=n_components, random_state=42)
        self._svd.fit(tfidf)
        self.dimension = n_components
        self.name = f"tfidf+svd({n_components})"
        self._fitted = True
        logger.info("Offline embedder fitted: %d docs -> %d dimensions",
                    len(corpus), n_components)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        if not self._fitted or self._svd is None:
            raise RuntimeError(
                "The offline embedder must be fitted on the corpus before use."
            )
        if not texts:
            return np.zeros((0, self.dimension), dtype="float32")
        tfidf = self._vectorizer.transform(list(texts))
        return _l2_normalise(self._svd.transform(tfidf))


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------
_embedder: Optional[Embedder] = None
_lock = threading.Lock()


def _create_embedder() -> Embedder:
    if config.FORCE_OFFLINE_EMBEDDINGS:
        logger.info("FORCE_OFFLINE_EMBEDDINGS=1 -> using the TF-IDF+SVD backend.")
        return TfidfSvdEmbedder()

    try:
        embedder = SentenceTransformerEmbedder(config.EMBEDDING_MODEL)
        logger.info("Embedding backend: %s (%d dimensions)", embedder.name, embedder.dimension)
        return embedder
    except Exception as exc:
        # Most commonly: no internet on first run, so the model cannot download.
        logger.warning(
            "Could not load '%s' (%s). Falling back to the offline TF-IDF+SVD "
            "embedder; retrieval will still work.", config.EMBEDDING_MODEL, exc,
        )
        return TfidfSvdEmbedder()


def get_embedder(force_reload: bool = False) -> Embedder:
    """Process-wide embedder. Loading the neural model is slow, so cache it."""
    global _embedder
    with _lock:
        if _embedder is None or force_reload:
            _embedder = _create_embedder()
        return _embedder


def reset_embedder() -> None:
    """Used by the test suite to switch backends between runs."""
    global _embedder
    with _lock:
        _embedder = None
