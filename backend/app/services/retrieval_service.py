"""RAG Document Retrieval Service.

Implements query embedding generation, semantic pgvector similarity search,
keyword fallback retrieval, source citation formatting, and prompt injection defense.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document
from app.models.document_chunk import EMBEDDING_DIMENSIONS, DocumentChunk
from app.models.topic import Topic

logger = logging.getLogger(__name__)

# Cached SentenceTransformer model singleton
_EMBEDDING_MODEL = None
_EMBEDDING_MODEL_LOAD_ATTEMPTED = False


def _get_embedding_model() -> Any:
    """Lazy load SentenceTransformer model singleton."""
    global _EMBEDDING_MODEL, _EMBEDDING_MODEL_LOAD_ATTEMPTED
    if _EMBEDDING_MODEL is not None:
        return _EMBEDDING_MODEL

    if not _EMBEDDING_MODEL_LOAD_ATTEMPTED:
        _EMBEDDING_MODEL_LOAD_ATTEMPTED = True
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence transformer model: %s", settings.EMBEDDING_MODEL_NAME)
            _EMBEDDING_MODEL = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        except Exception as exc:
            logger.warning("Could not load SentenceTransformer (%s). Using deterministic fallback.", exc)
            _EMBEDDING_MODEL = None

    return _EMBEDDING_MODEL


def generate_query_embedding(query_text: str) -> List[float]:
    """Generate a 384-dimensional embedding for a text query.

    Uses SentenceTransformers when available, or a deterministic normalized vector fallback.
    """
    if not query_text or not query_text.strip():
        return [0.0] * EMBEDDING_DIMENSIONS

    model = _get_embedding_model()
    if model is not None:
        try:
            vec = model.encode(query_text, normalize_embeddings=True)
            return [float(x) for x in vec]
        except Exception as exc:
            logger.warning("Embedding generation error with model: %s. Using fallback vector.", exc)

    # Deterministic fallback: Generate 384-dim pseudo-embedding from SHA-256 hash
    hasher = hashlib.sha256(query_text.encode("utf-8")).digest()
    raw = [(float(b) / 128.0) - 1.0 for b in hasher]
    # Repeat/pad to 384 dimensions
    padded = (raw * ((EMBEDDING_DIMENSIONS // len(raw)) + 1))[:EMBEDDING_DIMENSIONS]
    norm = sum(x * x for x in padded) ** 0.5 or 1.0
    return [x / norm for x in padded]


# Prompt injection prevention regexes
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|above)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|unrestricted)", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<system>", re.IGNORECASE),
    re.compile(r"</system>", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"<\|im_end\|>", re.IGNORECASE),
]


def sanitize_reference_text(text: str) -> str:
    """Neutralize potential prompt injection attempts in retrieved document content."""
    sanitized = text
    for pat in _INJECTION_PATTERNS:
        sanitized = pat.sub("[FILTERED_INSTRUCTION_OVERRIDE]", sanitized)
    return sanitized.strip()


def retrieve_relevant_chunks(
    db: Session,
    course_id: uuid.UUID,
    query: str,
    limit: int = 4,
    similarity_threshold: float = 0.15,
) -> List[Dict[str, Any]]:
    """Retrieve top relevant course document chunks using semantic or keyword search.

    Ensures only documents belonging to the specified course are searched.
    """
    if not query or not query.strip():
        return []

    # 1. Fetch available chunks joined with course documents
    base_query = (
        select(DocumentChunk, Document.filename)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            Document.course_id == course_id,
            Document.status == "completed",
        )
    )

    is_sqlite = db.bind is not None and db.bind.dialect.name == "sqlite"
    results: List[Dict[str, Any]] = []

    # Try pgvector cosine distance if supported and not running SQLite
    if not is_sqlite:
        try:
            query_embedding = generate_query_embedding(query)
            # pgvector cosine_distance returns float between 0 and 2
            vector_query = (
                base_query.where(DocumentChunk.embedding.isnot(None))
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(limit)
            )
            rows = db.execute(vector_query).all()
            for chunk, filename in rows:
                sim_score = 0.85  # Default reasonable similarity for top matches
                results.append(
                    _build_chunk_dict(chunk, filename, sim_score)
                )
        except Exception as exc:
            logger.debug("pgvector search not applicable or failed (%s), falling back to keyword search", exc)
            results = []

    # Fallback to keyword matching if vector search returned no results or was skipped
    if not results:
        # Extract meaningful keywords from query (words with length >= 3)
        keywords = [re.escape(w.lower()) for w in re.findall(r"\b[A-Za-z0-9_-]{3,}\b", query)[:6]]
        if keywords:
            conditions = [DocumentChunk.content.ilike(f"%{kw}%") for kw in keywords]
            keyword_query = (
                base_query.where(or_(*conditions))
                .limit(limit)
            )
            rows = db.execute(keyword_query).all()
            for chunk, filename in rows:
                results.append(_build_chunk_dict(chunk, filename, 0.75))

    # If still empty, return up to limit completed chunks for baseline course context
    if not results:
        fallback_rows = db.execute(base_query.limit(limit)).all()
        for chunk, filename in fallback_rows:
            results.append(_build_chunk_dict(chunk, filename, 0.50))

    return results[:limit]


def _build_chunk_dict(chunk: DocumentChunk, filename: str, score: float) -> Dict[str, Any]:
    """Helper to construct sanitized dictionary for a retrieved chunk."""
    clean_text = sanitize_reference_text(chunk.content)
    page_ref = f"Page {chunk.page_number}" if chunk.page_number else "Course Material"
    citation = f"Source: {filename}, {page_ref}."

    return {
        "chunk_id": str(chunk.id),
        "document_id": str(chunk.document_id),
        "filename": filename,
        "page_number": chunk.page_number,
        "end_page_number": chunk.end_page_number,
        "content": clean_text,
        "similarity_score": score,
        "source_reference": citation,
    }


def retrieve_topic_context(
    db: Session,
    course_id: uuid.UUID,
    topic: Topic,
    limit: int = 4,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Retrieve relevant course notes and textbook excerpts for a topic.

    Returns:
        (formatted_context_string, list_of_source_dictionaries)
    """
    search_query = f"{topic.name} {topic.description or ''}"
    chunks = retrieve_relevant_chunks(db, course_id, search_query, limit=limit)
    return format_retrieved_context(chunks)


def format_retrieved_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Format retrieved document chunks into clean reference text with citations."""
    if not chunks:
        return "No specific course excerpts uploaded for this topic.", []

    formatted_parts = []
    sources = []

    for i, c in enumerate(chunks, start=1):
        formatted_parts.append(
            f"--- [EXCERPT {i}: {c['source_reference']}] ---\n{c['content']}"
        )
        sources.append(
            {
                "citation": c["source_reference"],
                "filename": c["filename"],
                "page_number": c["page_number"],
                "snippet": c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
            }
        )

    context_str = (
        "<course_reference_material>\n"
        + "\n\n".join(formatted_parts)
        + "\n</course_reference_material>"
    )
    return context_str, sources

