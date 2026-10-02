"""
vector_store.py
===============

A thin, explainable wrapper around a FAISS index.

Why FAISS
---------
FAISS (Facebook AI Similarity Search) is a local library -- no server, no
account, no network. For a corpus of this size we use ``IndexFlatIP``:

  * *Flat*  -- vectors are stored as-is and every query is compared against
    every stored vector. It is exact (no approximation error) and, at a few
    hundred chunks, instant.
  * *IP*    -- inner product. Because ``embedder.py`` L2-normalises every
    vector, the inner product of two vectors equals their **cosine
    similarity**, giving a score in [-1, 1] where 1 means identical direction.

So "vector similarity search" here is precisely: normalise everything, then
take the dot product of the query vector with each stored vector and keep the
highest k. That is a sentence anyone can defend in a viva.

Persistence
-----------
The index is written to ``data/vector_store/`` alongside a JSON file holding
the chunk metadata, so the (slow) embedding step runs once rather than on
every server start.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .chunker import Chunk

logger = logging.getLogger("career_engine.rag.vector_store")

INDEX_FILENAME = "faiss.index"
CHUNKS_FILENAME = "chunks.json"
MANIFEST_FILENAME = "manifest.json"


class VectorStore:
    """An in-memory FAISS index plus the chunks it was built from."""

    def __init__(self, dimension: int, backend: str = "unknown", model: str = "unknown"):
        import faiss

        self._faiss = faiss
        self.dimension = dimension
        self.backend = backend
        self.model = model
        # Inner product over unit vectors == cosine similarity.
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: List[Chunk] = []

    # -- building ----------------------------------------------------------
    def add(self, chunks: Sequence[Chunk], vectors: np.ndarray) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(
                f"Chunk/vector count mismatch: {len(chunks)} chunks vs {len(vectors)} vectors."
            )
        if len(chunks) == 0:
            return
        vectors = np.ascontiguousarray(np.asarray(vectors, dtype="float32"))
        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Expected {self.dimension}-dimensional vectors, got {vectors.shape[1]}."
            )
        self.index.add(vectors)
        self.chunks.extend(chunks)

    # -- searching ---------------------------------------------------------
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 6,
        role_id: Optional[str] = None,
        candidate_pool: int = 80,
        max_per_document: int = 4,
    ) -> List[Tuple[Chunk, float]]:
        """
        Return the ``top_k`` most similar chunks as ``(chunk, cosine_score)``.

        ``role_id`` applies a post-filter: we retrieve a larger pool first and
        then keep only chunks belonging to that role. Filtering *after* search
        (rather than searching a separate per-role index) keeps one index and
        lets us fall back to unfiltered results if the role has no chunks.

        ``max_per_document`` diversifies the result set. Chunks from a single
        job description tend to score similarly, so a pure top-k can return six
        lines from one company and none from the other. Capping the number of
        chunks per document spreads the evidence across employers, which makes
        the retrieved requirements more representative of the role as a whole.
        Any leftover slots are filled by relaxing the cap, so we never return
        fewer results than we could.
        """
        if self.is_empty:
            return []

        vector = np.ascontiguousarray(
            np.asarray(query_vector, dtype="float32").reshape(1, -1)
        )
        # A role filter discards most of the pool, so search exhaustively when
        # one is active. The index is flat and small, making this effectively
        # free while guaranteeing the per-document cap has enough to work with.
        pool = self.size if role_id else min(max(top_k, candidate_pool), self.size)
        scores, indices = self.index.search(vector, pool)

        eligible: List[Tuple[Chunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:                      # FAISS pads with -1 when short
                continue
            chunk = self.chunks[int(idx)]
            if role_id and chunk.role_id and chunk.role_id != role_id:
                continue
            eligible.append((chunk, float(score)))

        # First pass: honour the per-document cap (results stay score-ordered).
        results: List[Tuple[Chunk, float]] = []
        per_document: Dict[str, int] = {}
        overflow: List[Tuple[Chunk, float]] = []
        for chunk, score in eligible:
            if per_document.get(chunk.document_id, 0) < max_per_document:
                per_document[chunk.document_id] = per_document.get(chunk.document_id, 0) + 1
                results.append((chunk, score))
            else:
                overflow.append((chunk, score))
            if len(results) >= top_k:
                break

        # Second pass: if diversity left us short, top up from the overflow.
        if len(results) < top_k:
            results.extend(overflow[: top_k - len(results)])
            results.sort(key=lambda pair: pair[1], reverse=True)

        if not results and role_id:
            # The requested role has no chunks -- better to return the closest
            # matches from the whole corpus than to return nothing.
            return self.search(query_vector, top_k=top_k, role_id=None)
        return results

    # -- properties --------------------------------------------------------
    @property
    def size(self) -> int:
        return int(self.index.ntotal)

    @property
    def is_empty(self) -> bool:
        return self.size == 0

    def stats(self) -> Dict[str, object]:
        documents = {c.document_id for c in self.chunks}
        sections: Dict[str, int] = {}
        for chunk in self.chunks:
            sections[chunk.section] = sections.get(chunk.section, 0) + 1
        return {
            "chunks": self.size,
            "documents": len(documents),
            "dimension": self.dimension,
            "index_type": type(self.index).__name__,
            "similarity": "cosine (inner product over L2-normalised vectors)",
            "embedding_backend": self.backend,
            "embedding_model": self.model,
            "chunks_per_section": dict(sorted(sections.items())),
        }

    # -- persistence -------------------------------------------------------
    def save(self, directory: pathlib.Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self._faiss.write_index(self.index, str(directory / INDEX_FILENAME))
        (directory / CHUNKS_FILENAME).write_text(
            json.dumps([c.to_dict() for c in self.chunks], indent=1, ensure_ascii=False)
        )
        (directory / MANIFEST_FILENAME).write_text(json.dumps({
            "dimension": self.dimension,
            "backend": self.backend,
            "model": self.model,
            "chunk_count": self.size,
        }, indent=2))
        logger.info("Saved vector store (%d chunks) to %s", self.size, directory)

    @classmethod
    def load(cls, directory: pathlib.Path) -> Optional["VectorStore"]:
        """Load a persisted store, or return ``None`` if it is absent/unusable."""
        index_path = directory / INDEX_FILENAME
        chunks_path = directory / CHUNKS_FILENAME
        manifest_path = directory / MANIFEST_FILENAME
        if not (index_path.exists() and chunks_path.exists() and manifest_path.exists()):
            return None

        try:
            import faiss

            manifest = json.loads(manifest_path.read_text())
            store = cls(
                dimension=int(manifest["dimension"]),
                backend=str(manifest.get("backend", "unknown")),
                model=str(manifest.get("model", "unknown")),
            )
            store.index = faiss.read_index(str(index_path))
            store.chunks = [Chunk.from_dict(d) for d in json.loads(chunks_path.read_text())]
            if store.index.ntotal != len(store.chunks):
                logger.warning("Persisted store is inconsistent; it will be rebuilt.")
                return None
            logger.info("Loaded vector store (%d chunks) from %s", store.size, directory)
            return store
        except Exception as exc:
            logger.warning("Could not load persisted vector store (%s); rebuilding.", exc)
            return None
