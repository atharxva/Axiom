from chromadb.api.models.Collection import Collection
from app.retrieval.bm25_retriever import BM25Retriever

class HybridSearcher:
    def __init__(self, collection: Collection, bm25: BM25Retriever, rrf_k: int = 60):
        self.collection = collection
        self.bm25 = bm25
        self.rrf_k = rrf_k

    def search(self, query: str, top_k: int = 2) -> list[dict]:
        c_res = self.collection.query(query_texts=[query], n_results=top_k * 2)
        b_res = self.bm25.search(query, top_k=top_k * 2)

        docs = {cid: doc for cid, doc in zip(c_res["ids"][0], c_res["documents"][0])}
        docs.update({chunk.chunk_id: chunk.text for chunk, _ in b_res})

        c_ranks = {cid: r for r, cid in enumerate(c_res["ids"][0], start=1)}
        b_ranks = {chunk.chunk_id: r for r, (chunk, _) in enumerate(b_res, start=1)}

        scores = {}
        for cid in set(c_ranks.keys()) | set(b_ranks.keys()):
            scores[cid] = (
                (1.0 / (self.rrf_k + c_ranks[cid]) if cid in c_ranks else 0.0) +
                (1.0 / (self.rrf_k + b_ranks[cid]) if cid in b_ranks else 0.0)
            )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [{"chunk_id": cid, "score": s, "text": docs[cid]} for cid, s in ranked]
