from pydantic import BaseModel, Field
from typing import Any

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="User search query string")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of results to return (1-10)")

class SearchResultItem(BaseModel):
    chunk_id: str = Field(..., description="Deterministic SHA-256 chunk identifier")
    score: float = Field(..., description="FlashRank neural reranker confidence score (0.0 - 1.0)")
    text: str = Field(..., description="Document chunk text snippet")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Provenance metadata (source, section)")

class SearchResponse(BaseModel):
    query: str
    total_results: int
    latency_ms: float
    results: list[SearchResultItem]

class AuditRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Audit compliance question")
    session_id: str | None = Field(default=None, description="Optional chat session ID")
    user_id: str | None = Field(default=None, description="Optional user ID")
    doc_id: str | None = Field(default=None, description="Optional specific document ID to scope audit to")

class AuditResponse(BaseModel):

    query: str
    confidence_score: float
    is_sufficient: bool
    final_answer: str
    latency_ms: float

class UserProfileResponse(BaseModel):
    id: str
    username: str
    full_name: str | None
    role: str
    total_documents: int
    created_at: str

class DocumentItemResponse(BaseModel):
    id: str
    filename: str
    file_size_bytes: int
    chunk_count: int
    created_at: str

class ChatMessageItem(BaseModel):
    id: str
    role: str
    content: str
    confidence_score: float | None
    created_at: str

class ChatSessionItem(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int

