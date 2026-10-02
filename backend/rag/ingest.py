"""
ingest.py
=========

Builds the RAG index: the one-off (and cached) half of the pipeline.

    data/job_descriptions/*.json
        -> load documents
        -> chunk each document          (chunker.py)
        -> embed every chunk            (embedder.py)
        -> add to a FAISS index         (vector_store.py)
        -> persist to data/vector_store/

The persisted index is reused on later starts. It is rebuilt automatically
when the corpus changes (detected by hashing the job-description files) or
when the embedding backend changes -- vectors from one model are meaningless
to another, so mixing them would silently corrupt retrieval.
"""

from __future__ import annotations

import hashlib
import json
import logging
import pathlib
from typing import Dict, List, Optional, Tuple

import config

from .chunker import Chunk, chunk_job_description
from .embedder import Embedder, get_embedder
from .vector_store import MANIFEST_FILENAME, VectorStore

logger = logging.getLogger("career_engine.rag.ingest")


class IngestError(Exception):
    """The knowledge base could not be built."""


REQUIRED_FIELDS = ("id", "job_title", "company", "role_id")


def load_job_descriptions(directory: Optional[pathlib.Path] = None) -> List[Dict[str, object]]:
    """Load and validate every job-description JSON document."""
    directory = directory or config.JOB_DESCRIPTIONS_DIR
    if not directory.exists():
        raise IngestError(f"Job-description directory not found: {directory}")

    documents: List[Dict[str, object]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("Skipping malformed job description %s: %s", path.name, exc)
            continue
        missing = [f for f in REQUIRED_FIELDS if not document.get(f)]
        if missing:
            logger.error("Skipping %s: missing required field(s) %s", path.name, missing)
            continue
        document["_source_file"] = path.name
        documents.append(document)

    if not documents:
        raise IngestError(
            f"No usable job descriptions found in {directory}. "
            "Add at least one .json document to the knowledge base."
        )
    return documents


def corpus_fingerprint(directory: Optional[pathlib.Path] = None) -> str:
    """
    Content hash of the whole corpus.

    Stored in the index manifest so that editing, adding or removing a job
    description triggers an automatic rebuild on the next start.
    """
    directory = directory or config.JOB_DESCRIPTIONS_DIR
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.json")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def build_chunks(documents: List[Dict[str, object]]) -> List[Chunk]:
    chunks: List[Chunk] = []
    for document in documents:
        chunks.extend(chunk_job_description(document))
    if not chunks:
        raise IngestError("Chunking produced no text; check the job-description files.")
    return chunks


def _manifest_matches(directory: pathlib.Path, embedder: Embedder, fingerprint: str) -> bool:
    manifest_path = directory / MANIFEST_FILENAME
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError:
        return False
    return (
        manifest.get("corpus_fingerprint") == fingerprint
        and manifest.get("backend") == embedder.backend
        and manifest.get("model") == embedder.name
    )


def build_vector_store(
    force_rebuild: bool = False,
    directory: Optional[pathlib.Path] = None,
    persist_dir: Optional[pathlib.Path] = None,
) -> Tuple[VectorStore, Dict[str, object]]:
    """
    Return a ready-to-query vector store, building it only when necessary.

    Also returns a small report describing what happened, which the API exposes
    at ``/api/rag/status`` so the RAG stage is visible rather than implicit.
    """
    directory = directory or config.JOB_DESCRIPTIONS_DIR
    persist_dir = persist_dir or config.VECTOR_STORE_DIR

    documents = load_job_descriptions(directory)
    fingerprint = corpus_fingerprint(directory)
    embedder = get_embedder()

    # ---- try the cache ---------------------------------------------------
    # The offline backend must be re-fitted on the corpus before it can encode
    # a query, so it cannot use a cached index without re-running fit anyway.
    if not force_rebuild and not embedder.requires_fit:
        if _manifest_matches(persist_dir, embedder, fingerprint):
            store = VectorStore.load(persist_dir)
            if store is not None:
                return store, {
                    "rebuilt": False,
                    "source": "cache",
                    "documents": len(documents),
                    "chunks": store.size,
                    **store.stats(),
                }

    # ---- build from scratch ---------------------------------------------
    logger.info("Building RAG index from %d job descriptions...", len(documents))
    chunks = build_chunks(documents)
    texts = [c.text for c in chunks]

    if embedder.requires_fit:
        embedder.fit(texts)

    vectors = embedder.encode(texts)

    store = VectorStore(
        dimension=embedder.dimension,
        backend=embedder.backend,
        model=embedder.name,
    )
    store.add(chunks, vectors)

    try:
        store.save(persist_dir)
        manifest_path = persist_dir / MANIFEST_FILENAME
        manifest = json.loads(manifest_path.read_text())
        manifest["corpus_fingerprint"] = fingerprint
        manifest_path.write_text(json.dumps(manifest, indent=2))
    except OSError as exc:
        # A read-only data directory should not break the request path.
        logger.warning("Could not persist the vector store (%s); using it in memory.", exc)

    return store, {
        "rebuilt": True,
        "source": "built",
        "documents": len(documents),
        "chunks": store.size,
        **store.stats(),
    }
