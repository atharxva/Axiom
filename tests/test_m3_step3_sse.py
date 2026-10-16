import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.api.server import app

with TestClient(app) as client:
    query = "What is the containment deadline for a critical severity 1 security breach?"
    response = client.post("/api/search/stream", json={"query": query, "top_k": 2})
    
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    events = [line for line in response.text.split("\n\n") if line.strip()]
    print(f"✓ Received {len(events)} SSE stream events:")
    for e in events:
        first_line = e.splitlines()[0]
        payload = e.splitlines()[1] if len(e.splitlines()) > 1 else ""
        print(f"  [{first_line}] -> {payload[:80]}...")
    
    # Assert that status, result, and done events are all emitted
    assert any("event: status" in e for e in events)
    assert any("event: result" in e for e in events)
    assert any("event: done" in e for e in events)
    print("✓ SSE Real-Time Streaming Test Passed!")
