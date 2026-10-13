import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from app.ingestion.chunker import chunk_text

# 1. Load document and chunk via sliding window
doc_path = Path("data/raw_documents/enterprise_audit_policy.txt")
chunks = chunk_text(doc_path.read_text(encoding="utf-8"), source=doc_path.name, chunk_size=400, chunk_overlap=80)

# 2. Initialize persistent collection
client = chromadb.PersistentClient(path="./data/chroma_db")
collection = client.get_or_create_collection(
    name="enterprise_audit_docs",
    metadata={"hnsw:space": "cosine"}
)

# 3. Batch upsert chunks via Pydantic model serialization
collection.upsert(
    ids=[c.chunk_id for c in chunks],
    documents=[c.text for c in chunks],
    metadatas=[c.metadata.model_dump() for c in chunks]
)
print(f"✓ Successfully indexed {len(chunks)} chunks in collection '{collection.name}'")

# 4. Execute enterprise semantic query
query = "What is the retention period for financial transaction audit records?"
res = collection.query(query_texts=[query], n_results=1)

top_id = res["ids"][0][0]
top_doc = res["documents"][0][0]
sim = 1.0 - res["distances"][0][0]

print(f"\nQuery: '{query}'")
print(f"Top Match ID: {top_id} (Cosine Sim: {sim:.4f})\nSnippet:\n{top_doc}\n")

assert "7 years" in top_doc, "Retrieval failed to find the 7-year retention rule"
print("✓ Retrieval assertion passed: Precise audit rule identified!")
