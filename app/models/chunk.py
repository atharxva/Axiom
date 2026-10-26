import hashlib
from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    source: str = Field(..., description="Source document path or URL")
    page_number: int = Field(default=1, ge=1, description="1-indexed page number")
    section: str = Field(default="compliance_clause", description="Section or heading")
    user_id: str | None = Field(default=None, description="Owner user ID for tenant isolation")
    doc_id: str | None = Field(default=None, description="Document UUID for document-scoped search")


class DocumentChunk(BaseModel):
    text: str = Field(..., min_length=10, description="Chunk content")
    chunk_index: int = Field(..., ge=0, description="0-indexed sequence position")
    metadata: ChunkMetadata
    token_count: int = Field(default=0, ge=0)

    @property
    def chunk_id(self) -> str:
        if hasattr(self, "_hydrated_id"):
            return self._hydrated_id
        raw = f"{self.metadata.source}:{self.metadata.doc_id}:{self.chunk_index}:{self.text[:30]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_chroma_format(self) -> dict:
        return {
            "id": self.chunk_id,
            "document": self.text,
            "metadata": self.metadata.model_dump()
        }
