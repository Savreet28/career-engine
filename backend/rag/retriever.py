"""
retriever.py
============

The query half of the RAG pipeline.

    target role (+ optional pasted JD)
        -> build a query string
        -> embed the query with the SAME model used for the chunks
        -> cosine-similarity search over the FAISS index
        -> top-k job-description chunks, each with its similarity score

Two things are deliberate:

*  The query is embedded with the *same* embedder instance as the corpus. Using
   a different model would put the query in a different vector space and the
   scores would be meaningless.
*  Retrieved chunks are returned with their provenance and score, not merged
   into an opaque blob. The UI shows them verbatim, which is what makes
   Objective 2 "explainable" rather than "trust me".
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional

import config

from .chunker import Chunk, chunk_free_text
from .embedder import Embedder, get_embedder
from .ingest import build_vector_store
from .vector_store import VectorStore

logger = logging.getLogger("career_engine.rag.retriever")


class Retriever:
    """Wraps a built vector store and the embedder that produced it."""

    def __init__(self, store: VectorStore, embedder: Embedder, report: Dict[str, object]):
        self.store = store
        self.embedder = embedder
        self.report = report

    # -- query construction ------------------------------------------------
    @staticmethod
    def build_query(
        role_title: str,
        job_description_text: Optional[str] = None,
        seed_skills: Optional[List[str]] = None,
    ) -> str:
        """
        Compose the retrieval query.

        This is *query expansion*, a standard information-retrieval technique.
        The role title alone is a weak query -- two or three words, and the
        chunks do not contain the title. We therefore expand it in three ways:

        1. any pasted job description goes first: it is the strongest signal of
           what this particular employer wants;
        2. a handful of seed skills from the role catalogue, which put the query
           in the same vocabulary region as the chunks it should match;
        3. intent words about skills and tools.

        The wording deliberately avoids "qualifications": including it pulled
        degree requirements ("Bachelor's degree in ...") to the top, and those
        carry almost no skill evidence.

        Note that expansion does not make the requirement list circular. The
        role filter already narrows the index to this role's documents, and the
        matcher reads a deep slice of them, so skills the catalogue never
        mentions are still discovered from the retrieved text.
        """
        parts = [
            f"{role_title} required technical skills",
            f"programming languages, frameworks and tools used by a {role_title}",
            f"hands-on experience and responsibilities of a {role_title}",
        ]
        if seed_skills:
            parts.insert(0, "Skills: " + ", ".join(list(seed_skills)[:12]) + ".")
        if job_description_text and job_description_text.strip():
            # Cap the pasted text: an over-long query dilutes the embedding.
            snippet = " ".join(job_description_text.split()[:220])
            parts.insert(0, snippet)
        return " ".join(parts)

    # -- retrieval ---------------------------------------------------------
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        role_id: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        top_k = top_k or config.RAG_TOP_K
        if self.store.is_empty:
            return []

        query_vector = self.embedder.encode_one(query)
        hits = self.store.search(query_vector, top_k=top_k, role_id=role_id)

        results: List[Dict[str, object]] = []
        for rank, (chunk, score) in enumerate(hits, start=1):
            results.append({
                "rank": rank,
                "similarity": round(float(score), 4),
                "chunk_id": chunk.chunk_id,
                "text": str(chunk.metadata.get("raw_text") or chunk.text),
                "embedded_text": chunk.text,
                "source": chunk.source_label,
                "job_title": chunk.job_title,
                "company": chunk.company,
                "document_id": chunk.document_id,
                "role_id": chunk.role_id,
                "section": chunk.section,
                "requirement_kind": chunk.requirement_kind,
            })
        return results

    def retrieve_for_role(
        self,
        role_title: str,
        role_id: Optional[str] = None,
        job_description_text: Optional[str] = None,
        top_k: Optional[int] = None,
        restrict_to_role: bool = True,
        seed_skills: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        """
        Retrieve JD evidence for a target role.

        Returns the hits together with the query actually used, so the UI can
        show exactly what was asked of the index.
        """
        query = self.build_query(role_title, job_description_text, seed_skills)
        results = self.retrieve(
            query,
            top_k=top_k,
            role_id=role_id if restrict_to_role else None,
        )
        return {
            "query": query,
            "top_k": top_k or config.RAG_TOP_K,
            "role_filter": role_id if restrict_to_role else None,
            "results": results,
            "index": self.store.stats(),
        }

    # -- pasted job descriptions -------------------------------------------
    def rank_pasted_chunks(
        self,
        job_description_text: str,
        role_title: str,
        top_k: Optional[int] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        """
        Run the same retrieval machinery over a job description the user pasted.

        The pasted text is chunked and embedded on the fly, then ranked against
        the role query. This keeps user-supplied JDs first-class: they are
        retrieved over, not just keyword-scanned.

        ``query`` should be the SAME query string used for the knowledge-base
        search. Scoring both sets against one query is what makes their cosine
        similarities comparable, so the two can be merged into a single ranked
        list of evidence.

        ``top_k`` of ``None`` returns EVERY chunk of the pasted posting, ranked.
        That is the right default for requirement derivation: the user supplied
        this posting deliberately, so all of its requirements count, even the
        ones whose wording happens to rank low against the query. Pass an
        explicit ``top_k`` only when trimming the list for display.
        """
        chunks: List[Chunk] = chunk_free_text(job_description_text)
        if not chunks:
            return []

        # The offline TF-IDF backend can only encode text built from the
        # vocabulary it was fitted on; unseen pasted text still projects fine.
        try:
            chunk_vectors = self.embedder.encode([c.text for c in chunks])
            query_vector = self.embedder.encode_one(query or self.build_query(role_title))
        except RuntimeError as exc:
            logger.warning("Could not embed pasted job description: %s", exc)
            return []

        scores = chunk_vectors @ query_vector
        order = sorted(range(len(chunks)), key=lambda i: float(scores[i]), reverse=True)

        selected = order if top_k is None else order[:top_k]
        results: List[Dict[str, object]] = []
        for rank, i in enumerate(selected, start=1):
            chunk = chunks[i]
            results.append({
                "rank": rank,
                "similarity": round(float(scores[i]), 4),
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "embedded_text": chunk.text,
                "source": "Job description you provided",
                "job_title": role_title,
                "company": "Provided by user",
                "document_id": "pasted_job_description",
                "role_id": "",
                "section": "pasted",
                # Carry the chunk's own classification, which chunk_free_text
                # derived from the posting's headings ("Required skills:" vs
                # "Nice to have:"). Hard-coding "core" here made every skill in
                # a pasted posting a must-have.
                "requirement_kind": chunk.requirement_kind,
            })
        return results


# ---------------------------------------------------------------------------
# Singleton access -- building the index is expensive, so do it once.
# ---------------------------------------------------------------------------
_retriever: Optional[Retriever] = None
_lock = threading.Lock()


def get_retriever(force_rebuild: bool = False) -> Retriever:
    global _retriever
    with _lock:
        if _retriever is None or force_rebuild:
            store, report = build_vector_store(force_rebuild=force_rebuild)
            _retriever = Retriever(store, get_embedder(), report)
        return _retriever


def reset_retriever() -> None:
    global _retriever
    with _lock:
        _retriever = None
