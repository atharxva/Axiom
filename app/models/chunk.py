import hashlib
from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    source: str = Field(..., description="Source document path or URL")
    page_number: int = Field(default=1, ge=1, description="1-indexed page number")
    section: str = Field(default="general", description="Section or heading")

class DocumentChunk(BaseModel):
    text: str = Field(..., min_length=10, description="Chunk content")
    chunk_index: int = Field(..., ge=0, description="0-indexed sequence position")
    metadata: ChunkMetadata
    token_count: int = Field(default=0, ge=0)

    @property
    def chunk_id(self) -> str:
        raw = f"{self.metadata.source}:{self.chunk_index}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_chroma_format(self) -> dict:
        return {
            "id": self.chunk_id,
            "document": self.text,
            "metadata": self.metadata.model_dump()
        }
