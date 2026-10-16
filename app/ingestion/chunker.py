import re
from app.models.chunk import DocumentChunk, ChunkMetadata

def chunk_text(text: str, source: str, max_chars: int = 600) -> list[DocumentChunk]:
    """
    Section-Aware Chunker:
    Splits along numbered clauses (e.g. 2.1, 2.2, 2.3) or paragraphs (\n\n)
    to isolate discrete compliance rules without dilution.
    """
    # Insert boundary markers before major section/clause headers (e.g. "2.4 Working hours.")
    delimited = re.sub(r"(\n(?:\d+\.\d+|\b[A-Z]{2,}\b|\bSection\b)\s+[A-Za-z])", r"\n\n\1", text)
    paragraphs = [p.strip() for p in delimited.split("\n\n") if p.strip()]

    chunks: list[DocumentChunk] = []
    current = ""
    idx = 0

    for p in paragraphs:
        # If adding paragraph exceeds max_chars OR if paragraph starts a new numbered clause
        starts_new_clause = bool(re.match(r"^\d+\.\d+", p))
        if current and (len(current) + len(p) + 2 > max_chars or starts_new_clause):
            if len(current) >= 15:
                meta = ChunkMetadata(source=source, page_number=1, section="compliance_clause")
                chunks.append(DocumentChunk(text=current, chunk_index=idx, metadata=meta))
                idx += 1
            current = p
        else:
            current = f"{current}\n\n{p}".strip() if current else p

    if len(current) >= 15:
        meta = ChunkMetadata(source=source, page_number=1, section="compliance_clause")
        chunks.append(DocumentChunk(text=current, chunk_index=idx, metadata=meta))

    return chunks
