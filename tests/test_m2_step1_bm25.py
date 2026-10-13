import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.chunker import chunk_text
from app.retrieval.bm25_retriever import BM25Retriever

# 1. Load document and chunk
doc_path = Path("data/raw_documents/enterprise_audit_policy.txt")
chunks = chunk_text(doc_path.read_text(encoding="utf-8"), source=doc_path.name)

# 2. Build BM25 index over the chunks
retriever = BM25Retriever(chunks)

# 3. Query exact enterprise jargon
query = "WORM storage Object Lock"
results = retriever.search(query, top_k=1)

top_chunk, score = results[0]
print(f"Query: '{query}'")
print(f"BM25 Score: {score:.4f} | Chunk ID: {top_chunk.chunk_id}")
print(f"Snippet:\n{top_chunk.text}\n")

assert "WORM" in top_chunk.text and score > 0, "BM25 failed to match keyword"
print("✓ BM25 Lexical Keyword assertion passed!")
