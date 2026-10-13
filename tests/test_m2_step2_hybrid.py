import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from app.ingestion.chunker import chunk_text
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.hybrid_search import HybridSearcher

# 1. Load document and chunk
doc_path = Path("data/raw_documents/enterprise_audit_policy.txt")
chunks = chunk_text(doc_path.read_text(encoding="utf-8"), source=doc_path.name)

# 2. Connect to existing persistent Chroma collection & BM25
client = chromadb.PersistentClient(path="./data/chroma_db")
collection = client.get_collection("enterprise_audit_docs")
bm25 = BM25Retriever(chunks)

# 3. Initialize Hybrid Engine & Execute Dual Search
hybrid = HybridSearcher(collection=collection, bm25=bm25)
query = "WORM storage and retention period for financial transaction records"
results = hybrid.search(query, top_k=2)

print(f"Hybrid Query: '{query}'\n")
for i, res in enumerate(results, start=1):
    print(f"Rank {i} | Chunk: {res['chunk_id']} | RRF Score: {res['score']:.5f}")
    print(f"Snippet:\n{res['text'][:120]}...\n")

assert len(results) > 0 and ("WORM" in results[0]["text"] or "Retention" in results[0]["text"])
print("✓ Hybrid Search Fusion test passed!")
