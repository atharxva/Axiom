import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from app.ingestion.chunker import chunk_text
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.reranker import RerankerService

# 1. Load document with paragraph-aware chunker
doc_path = Path("data/raw_documents/enterprise_audit_policy.txt")
chunks = chunk_text(doc_path.read_text(encoding="utf-8"), source=doc_path.name)

# 2. Reset and sync fresh paragraph chunks to ChromaDB
client = chromadb.PersistentClient(path="./data/chroma_db")
try:
    client.delete_collection("enterprise_audit_docs")
except Exception:
    pass
collection = client.create_collection("enterprise_audit_docs", metadata={"hnsw:space": "cosine"})
collection.upsert(
    ids=[c.chunk_id for c in chunks],
    documents=[c.text for c in chunks],
    metadatas=[c.metadata.model_dump() for c in chunks]
)

# 3. Execute Hybrid Search + FlashRank Reranker
hybrid = HybridSearcher(collection=collection, bm25=BM25Retriever(chunks))
reranker = RerankerService()

query = "What is the containment deadline for a critical severity 1 security breach?"
candidates = hybrid.search(query, top_k=3)
final_results = reranker.rerank(query, candidates, top_k=1)

top = final_results[0]
print(f"Query: '{query}'")
print(f"FlashRank Score: {top['score']:.4f} | ID: {top['chunk_id']}")
print(f"Snippet:\n{top['text']}\n")

assert "1 hour" in top["text"], "Reranker failed to prioritize the 1-hour containment rule"
print("✓ Neural Reranker precision test passed: Exact 1-hour containment rule retrieved!")
