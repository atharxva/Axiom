import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError
from app.models.chunk import DocumentChunk, ChunkMetadata

# 1. Verify schema contract & Chroma serialization
meta = ChunkMetadata(source="audit_policy.pdf", page_number=3, section="retention")
chunk = DocumentChunk(
    text="Audit records must be retained for at least 7 years in secure cold storage.",
    chunk_index=0,
    metadata=meta
)

payload = chunk.to_chroma_format()
print(f"Generated Deterministic ID: {payload['id']}")
print(f"Serialized Metadata       : {payload['metadata']}")

# 2. Assert ID determinism across instances
chunk_replay = DocumentChunk(text="Alternative text with same coordinates", chunk_index=0, metadata=meta)
assert chunk.chunk_id == chunk_replay.chunk_id, "IDs must match for identical (source, index)"
print("✓ Deterministic ID assertion passed.")

# 3. Verify validation guardrail on corrupt/too-short data
try:
    DocumentChunk(text="Short", chunk_index=1, metadata=meta)
except ValidationError as e:
    print(f"✓ Guardrail active: Rejected invalid text ({e.errors()[0]['msg']})")
