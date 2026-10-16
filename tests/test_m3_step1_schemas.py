import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError
from app.models.schemas import SearchRequest, SearchResultItem, SearchResponse

# 1. Verify valid request defaults and bounds
req = SearchRequest(query="WORM storage retention")
assert req.top_k == 3, "Default top_k should be 3"
print(f"✓ Valid Request: query='{req.query}', top_k={req.top_k}")

# 2. Verify bounds guardrail (top_k > 10 should fail)
try:
    SearchRequest(query="test", top_k=50)
    assert False, "Should fail on top_k > 10"
except ValidationError:
    print("✓ Guardrail active: Rejected top_k > 10")

# 3. Verify response schema serialization
item = SearchResultItem(chunk_id="abc123", score=0.992, text="Sample text", metadata={"source": "test.txt"})
resp = SearchResponse(query=req.query, total_results=1, latency_ms=12.4, results=[item])
assert len(resp.results) == 1 and resp.results[0].score == 0.992
print(f"✓ Response serialization valid: {resp.model_dump_json()[:70]}...")
