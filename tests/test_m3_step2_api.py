import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.api.server import app

# TestClient triggers the FastAPI lifespan startup event (loads models once)
with TestClient(app) as client:
    # 1. Verify health check
    health_res = client.get("/health")
    assert health_res.status_code == 200
    print(f"✓ Health Check: {health_res.json()}")

    # 2. Test valid search request
    query = "What is the containment deadline for a critical severity 1 security breach?"
    search_res = client.post("/api/search", json={"query": query, "top_k": 2})
    assert search_res.status_code == 200
    
    data = search_res.json()
    print(f"✓ Search HTTP 200: latency={data['latency_ms']}ms, results={data['total_results']}")
    
    top = data["results"][0]
    print(f"Top Result [{top['chunk_id']}] (Score: {top['score']}):\n{top['text'][:130]}...\n")
    assert "1 hour" in top["text"]
    print("✓ Full API Pipeline Integration Passed!")
