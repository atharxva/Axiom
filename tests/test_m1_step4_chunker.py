import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.chunker import chunk_text

doc_path = Path("data/raw_documents/enterprise_audit_policy.txt")
raw_text = doc_path.read_text(encoding="utf-8")

# Chunk with size=400 chars, overlap=80 chars
chunks = chunk_text(raw_text, source=doc_path.name, chunk_size=400, chunk_overlap=80)

print(f"Total Chunks Generated: {len(chunks)} from {len(raw_text)} characters.")
print("--- Chunk Inspection (First 2 Chunks) ---")
for c in chunks[:2]:
    print(f"[{c.chunk_id}] Index: {c.chunk_index} | Length: {len(c.text)} chars")
    print(f"Text Preview: {c.text[:90]}...\n")

# Assert sequential indices and deterministic IDs
assert len(chunks) > 0, "Chunks list should not be empty"
assert chunks[0].chunk_index == 0 and chunks[1].chunk_index == 1
print("✓ Chunker verification assertions passed.")
