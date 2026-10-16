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

class AuditResponse(BaseModel):
    query: str
    confidence_score: float
    is_sufficient: bool
    final_answer: str
    latency_ms: float
