import json, time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import chromadb

from app.ingestion.chunker import chunk_text
from app.ingestion.extractor import extract_text_from_file
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.reranker import RerankerService
from app.retrieval.audit_graph import build_audit_graph
from app.models.schemas import SearchRequest, SearchResponse, SearchResultItem, AuditRequest, AuditResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    doc_path = Path("data/raw_documents/enterprise_audit_policy.txt")
    doc = doc_path.read_text(encoding="utf-8") if doc_path.exists() else ""
    chunks = chunk_text(doc, source="enterprise_audit_policy.txt") if doc else []
    
    app.state.client = chromadb.PersistentClient(path="./data/chroma_db")
    app.state.coll = app.state.client.get_or_create_collection("enterprise_audit_docs", metadata={"hnsw:space": "cosine"})
    app.state.chunks = chunks
    app.state.bm25 = BM25Retriever(chunks) if chunks else None
    app.state.hybrid = HybridSearcher(collection=app.state.coll, bm25=app.state.bm25) if app.state.bm25 else None
    app.state.reranker = RerankerService()
    if app.state.hybrid:
        app.state.audit_graph = build_audit_graph(app.state.hybrid, app.state.reranker, min_confidence=0.50)
    yield

app = FastAPI(title="AxiomRAG Engine", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    chunk_count = len(getattr(app.state, "chunks", []))
    return {"status": "healthy", "service": "AxiomRAG", "indexed_chunks": chunk_count}

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()
    raw_text = extract_text_from_file(content, file.filename)
    if len(raw_text) < 10:
        return {"status": "error", "message": "Extracted document text is too short or empty."}

    new_chunks = chunk_text(raw_text, source=file.filename)
    app.state.coll.upsert(
        ids=[c.chunk_id for c in new_chunks],
        documents=[c.text for c in new_chunks],
        metadatas=[c.metadata.model_dump() for c in new_chunks]
    )
    
    app.state.chunks = getattr(app.state, "chunks", []) + new_chunks
    app.state.bm25 = BM25Retriever(app.state.chunks)
    app.state.hybrid = HybridSearcher(collection=app.state.coll, bm25=app.state.bm25)
    app.state.audit_graph = build_audit_graph(app.state.hybrid, app.state.reranker, min_confidence=0.50)
    
    return {"status": "success", "filename": file.filename, "new_chunks": len(new_chunks), "total_chunks": len(app.state.chunks)}

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
    return AuditResponse(query=payload.query, confidence_score=round(res["confidence_score"], 4), is_sufficient=res["is_sufficient"], final_answer=res["final_answer"], latency_ms=ms)

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
