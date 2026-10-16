import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from app.ingestion.chunker import chunk_text
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.reranker import RerankerService
from app.retrieval.audit_graph import build_audit_graph

# Setup warm engines
doc = Path("data/raw_documents/enterprise_audit_policy.txt").read_text(encoding="utf-8")
chunks = chunk_text(doc, source="enterprise_audit_policy.txt")
client = chromadb.PersistentClient(path="./data/chroma_db")
coll = client.get_collection("enterprise_audit_docs")
hybrid = HybridSearcher(collection=coll, bm25=BM25Retriever(chunks))
reranker = RerankerService()

graph = build_audit_graph(hybrid, reranker, min_confidence=0.50)

# 1. Test Valid Compliance Query (Happy Path -> generate_node)
valid_query = "What is the containment deadline for a critical severity 1 security breach?"
res1 = graph.invoke({"query": valid_query})
print(f"--- Query 1: '{valid_query}' ---")
print(f"Confidence: {res1['confidence_score']:.4f} | Sufficient: {res1['is_sufficient']}")
print(f"Answer: {res1['final_answer'][:110]}...\n")
assert res1["is_sufficient"] is True and "1 hour" in res1["final_answer"]

# 2. Test Irrelevant / Out-of-Domain Query (Rejection Path -> fallback_node)
unrelated_query = "What is the corporate pet policy for bringing dogs to the office?"
res2 = graph.invoke({"query": unrelated_query})
print(f"--- Query 2 (Out-of-Domain): '{unrelated_query}' ---")
print(f"Confidence: {res2['confidence_score']:.4f} | Sufficient: {res2['is_sufficient']}")
print(f"Answer: {res2['final_answer']}\n")
assert res2["is_sufficient"] is False and "Audit Rejection" in res2["final_answer"]

print("✓ LangGraph State Machine Verification Passed (Both Paths Validated)!")
