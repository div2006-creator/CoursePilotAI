"""Pydantic schemas for Course Document Upload and PDF Processing."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field


class DocumentChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    end_page_number: Optional[int] = None
    token_count: Optional[int] = None

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    filename: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    extracted_text_length: Optional[int] = None
    chunk_count: int = 0
    status: str
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentSingleResponse(BaseModel):
    success: bool = True
    data: DocumentResponse
    message: Optional[str] = None


class DocumentListResponseData(BaseModel):
    documents: List[DocumentResponse]
    total: int


class DocumentListResponse(BaseModel):
    success: bool = True
    data: DocumentListResponseData
    message: Optional[str] = None


class DocumentDetailResponse(BaseModel):
    success: bool = True
    data: DocumentResponse
    chunks: List[DocumentChunkResponse] = Field(default_factory=list)
    message: Optional[str] = None

