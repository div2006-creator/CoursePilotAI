"""Document Processing & PDF Text Extraction Service for CoursePilot AI.

Supports PDF syllabus and lecture upload, file signature validation, PyMuPDF text extraction,
page-preserving chunking, and 384-dim pgvector embedding generation.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
import re
from typing import List, Optional, Tuple
import uuid

import fitz  # PyMuPDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import utc_now
from app.models.course import Course
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.retrieval_service import generate_query_embedding

logger = logging.getLogger(__name__)

# PDF Magic Bytes signature
PDF_MAGIC_BYTES = b"%PDF-"
MAX_FILE_SIZE = settings.max_upload_size_bytes
MAX_PAGE_COUNT = settings.MAX_PDF_PAGES
CHUNK_SIZE_CHARS = 800
CHUNK_OVERLAP_CHARS = 100


class DocumentValidationError(Exception):
    """Raised when an uploaded document fails validation."""


class DocumentNotFoundError(Exception):
    """Raised when requested document does not exist or access is denied."""


def _verify_course_ownership(db: Session, user_id: uuid.UUID, course_id: uuid.UUID) -> Course:
    course = db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    ).scalar_one_or_none()
    if not course:
        raise DocumentNotFoundError(f"Course {course_id} not found or access denied.")
    return course


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal or invalid characters."""
    clean = Path(filename).name
    # Keep alphanumeric, dot, hyphen, underscore
    clean = re.sub(r"[^\w\.\-]", "_", clean)
    return clean[:200] or "document.pdf"


def validate_pdf_bytes(file_bytes: bytes, filename: str) -> None:
    """Strictly validate file signature, size, corruption, and encryption."""
    if not file_bytes:
        raise DocumentValidationError("Uploaded file is completely empty.")

    if len(file_bytes) > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        raise DocumentValidationError(
            f"File size exceeds maximum limit of {max_mb} MB ({len(file_bytes)} bytes uploaded)."
        )

    # Validate Magic Signature
    if not file_bytes.startswith(PDF_MAGIC_BYTES):
        raise DocumentValidationError(
            "Invalid file format: File header does not match valid PDF signature (%PDF-)."
        )

    # Open with PyMuPDF to test corruption & encryption
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise DocumentValidationError(f"Corrupted or unreadable PDF file: {exc}") from exc

    if doc.is_encrypted:
        doc.close()
        raise DocumentValidationError(
            "Encrypted or password-protected PDF files cannot be processed. Please provide an unencrypted PDF."
        )

    if doc.page_count < 1:
        doc.close()
        raise DocumentValidationError("PDF contains no pages.")

    if doc.page_count > MAX_PAGE_COUNT:
        page_count = doc.page_count
        doc.close()
        raise DocumentValidationError(
            f"PDF exceeds the maximum allowed length of {MAX_PAGE_COUNT} pages (file contains {page_count} pages)."
        )

    doc.close()


def chunk_text_by_pages(
    pages_text: List[Tuple[int, str]],
    chunk_size: int = CHUNK_SIZE_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> List[dict]:
    """Divide text into meaningful chunks while preserving page references."""
    chunks: List[dict] = []
    chunk_idx = 0

    for page_num, text in pages_text:
        cleaned = text.strip()
        if not cleaned:
            continue

        # Split page text into overlapping windows
        start = 0
        text_len = len(cleaned)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            # Try to break at a natural sentence or word boundary if possible
            if end < text_len:
                boundary = cleaned.rfind(". ", start, end)
                if boundary != -1 and boundary > start + (chunk_size // 2):
                    end = boundary + 1
                else:
                    space = cleaned.rfind(" ", start, end)
                    if space != -1 and space > start + (chunk_size // 2):
                        end = space

            chunk_content = cleaned[start:end].strip()
            if chunk_content:
                words = chunk_content.split()
                chunks.append({
                    "chunk_index": chunk_idx,
                    "content": chunk_content,
                    "page_number": page_num,
                    "end_page_number": page_num,
                    "token_count": len(words),
                })
                chunk_idx += 1

            start = end - overlap if end < text_len else text_len
            if start >= text_len:
                break

    return chunks


def process_document_sync(
    db: Session,
    document: Document,
    file_bytes: bytes,
) -> Document:
    """Extract text from PDF, generate embeddings, and store chunks."""
    try:
        document.status = DocumentStatus.PROCESSING.value
        db.commit()

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = doc.page_count

        pages_text: List[Tuple[int, str]] = []
        total_extracted_chars = 0

        for page_idx in range(page_count):
            page = doc.load_page(page_idx)
            page_text = page.get_text("text") or ""
            # Strip null characters that cause PostgreSQL text column errors
            page_text = page_text.replace("\x00", "")
            pages_text.append((page_idx + 1, page_text))
            total_extracted_chars += len(page_text.strip())

        doc.close()

        # If zero extractable text (e.g. scanned image PDF without OCR)
        if total_extracted_chars == 0:
            document.status = DocumentStatus.OCR_REQUIRED.value
            document.page_count = page_count
            document.extracted_text_length = 0
            document.error_message = (
                "No digital text could be extracted from this PDF. It may be a scanned image "
                "or contain non-selectable fonts. Please upload a PDF with selectable text."
            )
            document.processed_at = utc_now()
            db.commit()
            return document

        # Chunk text
        chunks_data = chunk_text_by_pages(pages_text)

        # Clear any prior chunks if re-processing
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()

        # Generate embeddings and create DocumentChunk entities
        for c in chunks_data:
            emb = generate_query_embedding(c["content"])
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=c["chunk_index"],
                content=c["content"],
                page_number=c["page_number"],
                end_page_number=c["end_page_number"],
                token_count=c["token_count"],
                embedding=emb,
            )
            db.add(chunk)

        document.status = DocumentStatus.COMPLETED.value
        document.page_count = page_count
        document.extracted_text_length = total_extracted_chars
        document.error_message = None
        document.processed_at = utc_now()
        db.commit()
        db.refresh(document)
        return document

    except Exception as exc:
        logger.exception("Error processing document %s: %s", document.id, exc)
        document.status = DocumentStatus.FAILED.value
        document.error_message = f"Failed to extract document content: {str(exc)}"
        document.processed_at = utc_now()
        db.commit()
        db.refresh(document)
        return document


def upload_and_process_document(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    filename: str,
    file_bytes: bytes,
) -> Document:
    """Validate, persist physical file, and extract syllabus text."""
    _verify_course_ownership(db, user_id, course_id)
    clean_name = sanitize_filename(filename)
    validate_pdf_bytes(file_bytes, clean_name)

    # Save to disk
    upload_dir = settings.upload_dir_path / str(course_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    unique_suffix = uuid.uuid4().hex[:8]
    disk_filename = f"{Path(clean_name).stem}_{unique_suffix}.pdf"
    disk_path = upload_dir / disk_filename

    with open(disk_path, "wb") as f:
        f.write(file_bytes)

    # Create Document record
    document = Document(
        course_id=course_id,
        filename=clean_name,
        file_path=str(disk_path),
        file_size=len(file_bytes),
        status=DocumentStatus.UPLOADED.value,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Process extraction and embeddings
    return process_document_sync(db, document, file_bytes)


def get_course_documents(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
) -> List[Document]:
    """Retrieve all uploaded documents for a course."""
    _verify_course_ownership(db, user_id, course_id)
    docs = db.execute(
        select(Document)
        .where(Document.course_id == course_id)
        .order_by(Document.created_at.desc())
    ).scalars().all()
    return list(docs)


def get_document_by_id(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Document:
    """Retrieve a single document by ID, ensuring course and user ownership."""
    _verify_course_ownership(db, user_id, course_id)
    doc = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.course_id == course_id,
        )
    ).scalar_one_or_none()
    if not doc:
        raise DocumentNotFoundError(f"Document {document_id} not found in this course.")
    return doc


def delete_document(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    document_id: uuid.UUID,
) -> bool:
    """Delete a document and clean up its stored file on disk."""
    doc = get_document_by_id(db, user_id, course_id, document_id)
    file_path = Path(doc.file_path)

    # Remove database record (DocumentChunk rows deleted via CASCADE)
    db.delete(doc)
    db.commit()

    # Safely remove file on disk
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as exc:
        logger.warning("Could not delete physical file %s: %s", file_path, exc)

    return True


def retry_document_processing(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Document:
    """Re-read stored file from disk and re-run extraction and embedding."""
    doc = get_document_by_id(db, user_id, course_id, document_id)
    file_path = Path(doc.file_path)

    if not file_path.exists():
        raise DocumentValidationError(f"Original file for document {document_id} no longer exists on disk.")

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    return process_document_sync(db, doc, file_bytes)

