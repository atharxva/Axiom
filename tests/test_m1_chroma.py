import chromadb

client = chromadb.PersistentClient(path="./data/chroma_db")
collection = client.get_or_create_collection(
    name="audit_chunks",
    metadata={"hnsw:space": "cosine"}
)

docs = [
    "AxiomRAG enforces compliance and tamper-evident audit trails for financial records.",
    "PostgreSQL utilizes write-ahead logging (WAL) for crash recovery and durability.",
    "Hybrid search combines dense embeddings with sparse BM25 lexical token matching."
]
ids = ["chunk_001", "chunk_002", "chunk_003"]
metadatas = [
    {"source": "sec_compliance.pdf", "section": "audit"},
    {"source": "db_specs.pdf", "section": "storage"},
    {"source": "rag_design.pdf", "section": "retrieval"}
]

collection.upsert(documents=docs, ids=ids, metadatas=metadatas)

query = "How are compliance and audit records tracked in the system?"
results = collection.query(query_texts=[query], n_results=2)

print(f"\nQuery: '{query}'")
for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
    sim = 1.0 - dist
    print(f"-> [Cosine Sim: {sim:.4f}] Source: {meta['source']} | Content: {doc}")
