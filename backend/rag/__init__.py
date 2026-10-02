"""
Career Engine RAG package
=========================

Objective 2 of the project: Retrieval-Augmented Generation over job-description
data for explainable job/role matching.

The pipeline, in order:

    data/job_descriptions/*.json      documents
             |
        chunker.py                    split each JD into small labelled chunks
             |
        embedder.py                   turn every chunk into a dense vector
             |
        vector_store.py               FAISS index (cosine similarity)
             |
        ingest.py                     builds + persists the above, once
             |
        retriever.py                  query -> top-k most similar chunks

The retrieved chunks are NOT passed to an LLM to "decide" anything. They are
parsed with the shared skill taxonomy to derive the job requirements that the
deterministic matcher then scores the candidate against.
"""

from .chunker import Chunk, chunk_job_description
from .embedder import Embedder, get_embedder
from .retriever import Retriever, get_retriever
from .vector_store import VectorStore

__all__ = [
    "Chunk",
    "chunk_job_description",
    "Embedder",
    "get_embedder",
    "Retriever",
    "get_retriever",
    "VectorStore",
]
