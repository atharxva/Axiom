from chromadb.api.models.Collection import Collection
from app.retrieval.bm25_retriever import BM25Retriever

class HybridSearcher:
    def __init__(self, collection: Collection, bm25: BM25Retriever, rrf_k: int = 60):
        self.collection = collection
        self.bm25 = bm25
        self.rrf_k = rrf_k

    def search(
        self, 
        query: str, 
        top_k: int = 2,
        user_id: str | None = None,
        doc_id: str | None = None
    ) -> list[dict]:
        where_filter = None
        conditions = []
        if user_id:
            conditions.append({"user_id": user_id})
        if doc_id:
            conditions.append({"doc_id": doc_id})

        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        query_kwargs = {"query_texts": [query], "n_results": top_k * 2}
        if where_filter:
            query_kwargs["where"] = where_filter

        c_res = None
        try:
            if self.collection.count() > 0:
                c_res = self.collection.query(**query_kwargs)
        except Exception as e:
            print(f"Chroma query notice: {e}")

        b_res = self.bm25.search(query, top_k=top_k * 2, user_id=user_id, doc_id=doc_id) if self.bm25 else []

        docs = {}
        c_ranks = {}
        metas = {}
        if c_res and c_res.get("ids") and len(c_res["ids"]) > 0:
            docs = {cid: doc for cid, doc in zip(c_res["ids"][0], c_res["documents"][0])}
            c_ranks = {cid: r for r, cid in enumerate(c_res["ids"][0], start=1)}
            if c_res.get("metadatas"):
                metas = {cid: m for cid, m in zip(c_res["ids"][0], c_res["metadatas"][0])}

        b_ranks = {}
        for r, (chunk, _) in enumerate(b_res, start=1):
            docs[chunk.chunk_id] = chunk.text
            b_ranks[chunk.chunk_id] = r
            if chunk.chunk_id not in metas:
                metas[chunk.chunk_id] = chunk.metadata.model_dump()

        scores = {}
        for cid in set(c_ranks.keys()) | set(b_ranks.keys()):
            scores[cid] = (
                (1.0 / (self.rrf_k + c_ranks[cid]) if cid in c_ranks else 0.0) +
                (1.0 / (self.rrf_k + b_ranks[cid]) if cid in b_ranks else 0.0)
            )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            {
                "chunk_id": cid, 
                "score": s, 
                "text": docs[cid],
                "metadata": metas.get(cid, {})
            } 
            for cid, s in ranked
        ]

