from app.models.chunk import DocumentChunk, ChunkMetadata

def chunk_text(text: str, source: str, max_chars: int = 800) -> list[DocumentChunk]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[DocumentChunk] = []
    current = ""
    idx = 0

    for p in paragraphs:
        if current and len(current) + len(p) + 2 > max_chars:
            meta = ChunkMetadata(source=source, page_number=1, section="audit_policy")
            chunks.append(DocumentChunk(text=current, chunk_index=idx, metadata=meta))
            idx += 1
            current = p
        else:
            current = f"{current}\n\n{p}".strip() if current else p

    if len(current) >= 10:
        meta = ChunkMetadata(source=source, page_number=1, section="audit_policy")
        chunks.append(DocumentChunk(text=current, chunk_index=idx, metadata=meta))

    return chunks
