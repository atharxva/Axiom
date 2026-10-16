import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.api.server import app

with TestClient(app) as client:
    # 1. Test POST /api/audit on Happy Path
    q1 = "What is the containment deadline for a critical severity 1 security breach?"
    res1 = client.post("/api/audit", json={"query": q1})
    assert res1.status_code == 200
    data1 = res1.json()
    print(f"--- HTTP 200 Audit Response (Valid Query) ---")
    print(f"Query      : {data1['query']}")
    print(f"Confidence : {data1['confidence_score']} | Sufficient: {data1['is_sufficient']}")
    print(f"Latency    : {data1['latency_ms']}ms")
    print(f"Answer     : {data1['final_answer'][:110]}...\n")
    assert data1["is_sufficient"] is True and "1 hour" in data1["final_answer"]

    # 2. Test POST /api/audit on Rejection Path
    q2 = "What are the rules for adopting puppies in our corporate headquarters?"
    res2 = client.post("/api/audit", json={"query": q2})
    assert res2.status_code == 200
    data2 = res2.json()
    print(f"--- HTTP 200 Audit Response (Rejection Query) ---")
    print(f"Query      : {data2['query']}")
    print(f"Confidence : {data2['confidence_score']} | Sufficient: {data2['is_sufficient']}")
    print(f"Answer     : {data2['final_answer']}\n")
    assert data2["is_sufficient"] is False and "Audit Rejection" in data2["final_answer"]

    print("✓ Full HTTP LangGraph Audit Endpoint Integration Passed!")
