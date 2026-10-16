import json, time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import chromadb

from app.ingestion.chunker import chunk_text
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.reranker import RerankerService
from app.retrieval.audit_graph import build_audit_graph
from app.models.schemas import SearchRequest, SearchResponse, SearchResultItem, AuditRequest, AuditResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    doc = Path("data/raw_documents/enterprise_audit_policy.txt").read_text(encoding="utf-8")
    chunks = chunk_text(doc, source="enterprise_audit_policy.txt")
    client = chromadb.PersistentClient(path="./data/chroma_db")
    coll = client.get_collection("enterprise_audit_docs")
    
    app.state.hybrid = HybridSearcher(collection=coll, bm25=BM25Retriever(chunks))
    app.state.reranker = RerankerService()
    app.state.audit_graph = build_audit_graph(app.state.hybrid, app.state.reranker, min_confidence=0.50)
    yield

app = FastAPI(title="AxiomRAG Engine", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "AxiomRAG"}

@app.post("/api/search", response_model=SearchResponse)
async def search(payload: SearchRequest, req: Request):
    t0 = time.perf_counter()
    candidates = req.app.state.hybrid.search(payload.query, top_k=payload.top_k * 2)
    reranked = req.app.state.reranker.rerank(payload.query, candidates, top_k=payload.top_k)
    ms = round((time.perf_counter() - t0) * 1000, 2)
    items = [SearchResultItem(chunk_id=r["chunk_id"], score=r["score"], text=r["text"]) for r in reranked]
    return SearchResponse(query=payload.query, total_results=len(items), latency_ms=ms, results=items)

@app.post("/api/audit", response_model=AuditResponse)
async def audit(payload: AuditRequest, req: Request):
    t0 = time.perf_counter()
    res = req.app.state.audit_graph.invoke({"query": payload.query})
    ms = round((time.perf_counter() - t0) * 1000, 2)
    return AuditResponse(
        query=payload.query,
        confidence_score=round(res["confidence_score"], 4),
        is_sufficient=res["is_sufficient"],
        final_answer=res["final_answer"],
        latency_ms=ms
    )

@app.post("/api/search/stream")
async def search_stream(payload: SearchRequest, req: Request):
    async def event_generator():
        t0 = time.perf_counter()
        yield f"event: status\ndata: {json.dumps({'stage': 'hybrid_search', 'query': payload.query})}\n\n"
        candidates = req.app.state.hybrid.search(payload.query, top_k=payload.top_k * 2)
        yield f"event: status\ndata: {json.dumps({'stage': 'reranking', 'candidates': len(candidates)})}\n\n"
        reranked = req.app.state.reranker.rerank(payload.query, candidates, top_k=payload.top_k)
        for item in reranked:
            yield f"event: result\ndata: {json.dumps({'chunk_id': item['chunk_id'], 'score': item['score'], 'text': item['text']})}\n\n"
        ms = round((time.perf_counter() - t0) * 1000, 2)
        yield f"event: done\ndata: {json.dumps({'latency_ms': ms})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
