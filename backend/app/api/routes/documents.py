"""Document upload and management API routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentListResponseData,
    DocumentResponse,
    DocumentSingleResponse,
)
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentValidationError,
    delete_document,
    get_course_documents,
    get_document_by_id,
    retry_document_processing,
    upload_and_process_document,
)

router = APIRouter()


def _serialize_doc(doc) -> DocumentResponse:
    chunk_count = len(doc.chunks) if hasattr(doc, "chunks") and doc.chunks is not None else 0
    return DocumentResponse(
        id=doc.id,
        course_id=doc.course_id,
        filename=doc.filename,
        file_size=doc.file_size,
        page_count=doc.page_count,
        extracted_text_length=doc.extracted_text_length,
        chunk_count=chunk_count,
        status=doc.status,
        error_message=doc.error_message,
        processed_at=doc.processed_at,
        created_at=doc.created_at,
    )


@router.post(
    "/courses/{course_id}/documents/upload",
    response_model=DocumentSingleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a syllabus or study material PDF",
)
async def upload_document_endpoint(
    course_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentSingleResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload.",
        )

    content = await file.read()

    try:
        doc = upload_and_process_document(
            db=db,
            user_id=current_user.id,
            course_id=course_id,
            filename=file.filename,
            file_bytes=content,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the document: {str(exc)}",
        ) from exc

    return DocumentSingleResponse(
        success=True,
        data=_serialize_doc(doc),
        message=f"Document '{doc.filename}' processed successfully ({doc.status}).",
    )


@router.get(
    "/courses/{course_id}/documents",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all documents uploaded for a course",
)
def list_documents_endpoint(
    course_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    try:
        docs = get_course_documents(db, current_user.id, course_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    serialized = [_serialize_doc(d) for d in docs]
    return DocumentListResponse(
        success=True,
        data=DocumentListResponseData(documents=serialized, total=len(serialized)),
        message="Course documents retrieved successfully",
    )


@router.get(
    "/courses/{course_id}/documents/{document_id}",
    response_model=DocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details and chunks for a specific document",
)
def get_document_endpoint(
    course_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    try:
        doc = get_document_by_id(db, current_user.id, course_id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return DocumentDetailResponse(
        success=True,
        data=_serialize_doc(doc),
        chunks=[
            {
                "id": c.id,
                "document_id": c.document_id,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "page_number": c.page_number,
                "end_page_number": c.end_page_number,
                "token_count": c.token_count,
            }
            for c in doc.chunks
        ],
        message="Document details retrieved successfully",
    )


@router.delete(
    "/courses/{course_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a course document",
)
def delete_document_endpoint(
    course_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_document(db, current_user.id, course_id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/courses/{course_id}/documents/{document_id}/retry",
    response_model=DocumentSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry processing for a failed document",
)
def retry_document_endpoint(
    course_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentSingleResponse:
    try:
        doc = retry_document_processing(db, current_user.id, course_id, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return DocumentSingleResponse(
        success=True,
        data=_serialize_doc(doc),
        message=f"Document re-processed ({doc.status}).",
    )

