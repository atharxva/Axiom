import re
from app.models.chunk import DocumentChunk, ChunkMetadata

def chunk_text(
    text: str, 
    source: str, 
    max_chars: int = 600, 
    user_id: str | None = None, 
    doc_id: str | None = None,
    page_number: int = 1
) -> list[DocumentChunk]:
    """
    Section-Aware Chunker:
    Splits along numbered clauses (e.g. 2.1, 2.2, 2.3) or paragraphs (\n\n)
    to isolate discrete compliance rules without dilution.
    """
    # Split text into paragraphs
    raw_paras = text.split("\n\n")
    paragraphs: list[str] = []
    
    clause_pattern = re.compile(r"^(\d+\.(?:\d+)?|\bArticle\b|\bSection\b)\s+[A-Za-z]")

    for p in raw_paras:
        p_clean = p.strip()
        if not p_clean:
            continue
        # Check if internal lines start a new clause and split them
        lines = p_clean.split("\n")
        block: list[str] = []
        for line in lines:
            line_s = line.strip()
            if clause_pattern.match(line_s) and block:
                paragraphs.append("\n".join(block))
                block = [line_s]
            else:
                block.append(line_s)
        if block:
            paragraphs.append("\n".join(block))

    chunks: list[DocumentChunk] = []
    current = ""
    idx = 0

    for p in paragraphs:
        starts_new_clause = bool(clause_pattern.match(p))
        if current and (len(current) + len(p) + 2 > max_chars or starts_new_clause):
            if len(current) >= 15:
                meta = ChunkMetadata(
                    source=source, 
                    page_number=page_number, 
                    section="compliance_clause",
                    user_id=user_id,
                    doc_id=doc_id
                )
                chunks.append(DocumentChunk(text=current, chunk_index=idx, metadata=meta))
                idx += 1
            current = p
        else:
            current = f"{current}\n\n{p}".strip() if current else p

    if len(current) >= 15:
        meta = ChunkMetadata(
            source=source, 
            page_number=page_number, 
            section="compliance_clause",
            user_id=user_id,
            doc_id=doc_id
        )
        chunks.append(DocumentChunk(text=current, chunk_index=idx, metadata=meta))

    return chunks
