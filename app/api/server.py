import json, time, os, uuid
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import chromadb

from app.core.database import engine, Base, get_db, SessionLocal
from app.models.db_models import User, DocumentRecord, ChatSession, ChatMessage
from app.ingestion.chunker import chunk_text
from app.ingestion.extractor import extract_text_from_file, extract_pages_from_file
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.reranker import RerankerService
from app.retrieval.llm_service import LLMService
from app.retrieval.audit_graph import build_audit_graph
from app.models.schemas import (
    SearchRequest, SearchResponse, SearchResultItem, 
    AuditRequest, AuditResponse, UserProfileResponse,
    DocumentItemResponse, ChatMessageItem, ChatSessionItem
)

UPLOAD_DIR = Path("data/user_documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_USER_ID = "default-auditor-uuid"

def seed_default_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
        if not user:
            user = User(
                id=DEFAULT_USER_ID,
                username="auditor",
                full_name="Enterprise Auditor",
                role="Lead Compliance Officer"
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_default_user()

    app.state.client = chromadb.PersistentClient(path="./data/chroma_db")
    app.state.coll = app.state.client.get_or_create_collection("enterprise_audit_docs", metadata={"hnsw:space": "cosine"})
    
    # Initialize in-memory chunk list from persistent ChromaDB collection
    all_chunks = []
    try:
        chroma_data = app.state.coll.get()
        if chroma_data and chroma_data.get("ids") and len(chroma_data["ids"]) > 0:
            from app.models.chunk import DocumentChunk, ChunkMetadata
            for cid, doc, meta in zip(chroma_data["ids"], chroma_data["documents"], chroma_data["metadatas"]):
                m = ChunkMetadata(
                    source=meta.get("source", "document"),
                    page_number=meta.get("page_number", 1),
                    section=meta.get("section", "compliance_clause"),
                    user_id=meta.get("user_id"),
                    doc_id=meta.get("doc_id")
                )
                chunk = DocumentChunk(text=doc, chunk_index=0, metadata=m)
                chunk.__dict__["_hydrated_id"] = cid
                all_chunks.append(chunk)
    except Exception as e:
        print(f"Error hydrating BM25 from ChromaDB: {e}")

    # Fallback to sample policy if Chroma is completely empty
    if not all_chunks:
        doc_path = Path("data/raw_documents/enterprise_audit_policy.txt")
        if doc_path.exists():
            doc = doc_path.read_text(encoding="utf-8")
            all_chunks = chunk_text(doc, source="enterprise_audit_policy.txt")

    app.state.chunks = all_chunks
    app.state.bm25 = BM25Retriever(all_chunks) if all_chunks else None
    app.state.hybrid = HybridSearcher(collection=app.state.coll, bm25=app.state.bm25) if app.state.bm25 else None
    app.state.reranker = RerankerService()
    app.state.llm = LLMService()
    if app.state.hybrid:
        app.state.audit_graph = build_audit_graph(app.state.hybrid, app.state.reranker, min_confidence=0.50)
    yield

app = FastAPI(title="AxiomRAG Engine", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    chunk_count = len(getattr(app.state, "chunks", []))
    return {"status": "healthy", "service": "AxiomRAG", "indexed_chunks": chunk_count}

# ----------------- User Profile Endpoints -----------------
@app.get("/api/user/profile", response_model=UserProfileResponse)
async def get_profile(user_id: str = DEFAULT_USER_ID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    doc_count = db.query(DocumentRecord).filter(DocumentRecord.user_id == user.id).count()
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        total_documents=doc_count,
        created_at=user.created_at.isoformat()
    )

# ----------------- Document Endpoints -----------------
@app.get("/api/documents", response_model=list[DocumentItemResponse])
async def list_documents(user_id: str = DEFAULT_USER_ID, db: Session = Depends(get_db)):
    docs = db.query(DocumentRecord).filter(DocumentRecord.user_id == user_id).order_by(DocumentRecord.created_at.desc()).all()
    return [
        DocumentItemResponse(
            id=d.id,
            filename=d.filename,
            file_size_bytes=d.file_size_bytes,
            chunk_count=d.chunk_count,
            created_at=d.created_at.isoformat()
        )
        for d in docs
    ]

@app.get("/api/documents/{doc_id}/download")
async def get_document_file(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document file not found on disk")
    return FileResponse(doc.file_path, filename=doc.filename)

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...), 
    user_id: str = DEFAULT_USER_ID, 
    db: Session = Depends(get_db)
):
    pages = extract_pages_from_file(content, file.filename)
    if not pages or sum(len(txt) for _, txt in pages) < 10:
        return {"status": "error", "message": "Extracted document text is too short or empty."}

    # Save original file to user disk storage
    user_dir = UPLOAD_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    doc_uuid = str(uuid.uuid4())
    disk_path = user_dir / f"{doc_uuid}_{file.filename}"
    disk_path.write_bytes(content)

    new_chunks = []
    for page_num, page_txt in pages:
        if page_txt.strip():
            page_chunks = chunk_text(
                page_txt, 
                source=file.filename,
                user_id=user_id,
                doc_id=doc_uuid,
                page_number=page_num
            )
            new_chunks.extend(page_chunks)
    
    # Store in ChromaDB in safe batches
    app.state.coll = app.state.client.get_or_create_collection("enterprise_audit_docs", metadata={"hnsw:space": "cosine"})
    batch_size = 300
    for i in range(0, len(new_chunks), batch_size):
        batch = new_chunks[i:i + batch_size]
        app.state.coll.upsert(
            ids=[c.chunk_id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[c.metadata.model_dump() for c in batch]
        )
    
    app.state.chunks = getattr(app.state, "chunks", []) + new_chunks
    app.state.bm25 = BM25Retriever(app.state.chunks)
    app.state.hybrid = HybridSearcher(collection=app.state.coll, bm25=app.state.bm25)
    app.state.audit_graph = build_audit_graph(app.state.hybrid, app.state.reranker, min_confidence=0.50)

    # Persist document record in SQLite
    doc_record = DocumentRecord(
        id=doc_uuid,
        user_id=user_id,
        filename=file.filename,
        file_path=str(disk_path),
        file_size_bytes=len(content),
        chunk_count=len(new_chunks)
    )
    db.add(doc_record)
    db.commit()
    
    return {
        "status": "success", 
        "doc_id": doc_uuid,
        "filename": file.filename, 
        "new_chunks": len(new_chunks), 
        "total_chunks": len(app.state.chunks)
    }

# ----------------- Chat Session & Message Endpoints -----------------
@app.get("/api/chat/sessions", response_model=list[ChatSessionItem])
async def list_chat_sessions(user_id: str = DEFAULT_USER_ID, db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc()).all()
    return [
        ChatSessionItem(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
            message_count=len(s.messages)
        )
        for s in sessions
    ]

@app.post("/api/chat/sessions")
async def create_chat_session(title: str = "New Audit Session", user_id: str = DEFAULT_USER_ID, db: Session = Depends(get_db)):
    new_sess = ChatSession(title=title, user_id=user_id)
    db.add(new_sess)
    db.commit()
    db.refresh(new_sess)
    return {"id": new_sess.id, "title": new_sess.title, "created_at": new_sess.created_at.isoformat()}

@app.get("/api/chat/sessions/{session_id}/messages", response_model=list[ChatMessageItem])
async def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        ChatMessageItem(
            id=m.id,
            role=m.role,
            content=m.content,
            confidence_score=m.confidence_score,
            created_at=m.created_at.isoformat()
        )
        for m in sess.messages
    ]

# ----------------- Audit Streaming Pipeline -----------------
@app.post("/api/audit/stream")
async def audit_stream(payload: AuditRequest, req: Request, db: Session = Depends(get_db)):
    """Streams the entire RAG pipeline and persists the conversation to SQLite."""
    session_id = payload.session_id
    user_id = payload.user_id or DEFAULT_USER_ID

    # Auto-create session if none passed
    if not session_id:
        sess = ChatSession(user_id=user_id, title=payload.query[:40] + ("..." if len(payload.query) > 40 else ""))
        db.add(sess)
        db.commit()
        db.refresh(sess)
        session_id = sess.id
    else:
        sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not sess:
            sess = ChatSession(id=session_id, user_id=user_id, title=payload.query[:40])
            db.add(sess)
            db.commit()

    # Save user message
    user_msg = ChatMessage(session_id=session_id, role="user", content=payload.query)
    db.add(user_msg)
    db.commit()

    async def event_generator():
        t0 = time.perf_counter()
        yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"
        yield f"event: status\ndata: {json.dumps({'message': 'Querying Hybrid Index (BM25 + Chroma)...'})}\n\n"
        
        candidates = req.app.state.hybrid.search(
            payload.query, 
            top_k=25, 
            user_id=user_id, 
            doc_id=payload.doc_id
        ) if req.app.state.hybrid else []
        
        yield f"event: status\ndata: {json.dumps({'message': f'Reranking top {len(candidates)} candidate clauses...'})}\n\n"
        ranked = req.app.state.reranker.rerank(payload.query, candidates, top_k=3) if candidates else []
        top_chunk = ranked[0] if ranked else None
        top_meta = top_chunk.get("metadata", {}) if top_chunk else {}
        page_num = top_meta.get("page_number", 1)
        source_doc = top_meta.get("source", "")
        
        yield f"event: metadata\ndata: {json.dumps({'confidence': round(top_score, 4), 'is_sufficient': top_score >= 0.50, 'page_number': page_num, 'source': source_doc, 'snippet': top_chunk['text'][:250] if top_chunk else ''})}\n\n"
        
        full_answer = []
        if top_score < 0.50:
            rejection = f"Audit Notice: Confidence score ({top_score*100:.1f}%) is below verification threshold. No verified compliance policy found matching this inquiry."
            full_answer.append(rejection)
            yield f"event: token\ndata: {json.dumps({'token': rejection})}\n\n"
        else:
            top_doc = ranked[0]["text"]
            for token in req.app.state.llm.stream_audit_answer(payload.query, top_doc):
                full_answer.append(token)
                yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                
        ms = round((time.perf_counter() - t0) * 1000, 2)
        yield f"event: done\ndata: {json.dumps({'latency_ms': ms})}\n\n"

        # Persist assistant reply in background DB session
        save_db = SessionLocal()
        try:
            bot_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content="".join(full_answer),
                confidence_score=top_score
            )
            save_db.add(bot_msg)
            # Update session timestamp
            curr_sess = save_db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if curr_sess:
                curr_sess.updated_at = datetime.utcnow()
            save_db.commit()
        finally:
            save_db.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
