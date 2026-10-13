from flashrank import Ranker, RerankRequest

class RerankerService:
    def __init__(self, model_name: str = "ms-marco-TinyBERT-L-2-v2"):
        # Ultralight (4MB) cross-encoder model running on CPU via ONNX
        self.ranker = Ranker(model_name=model_name, cache_dir="./data/models")

    def rerank(self, query: str, candidates: list[dict], top_k: int = 2) -> list[dict]:
        if not candidates:
            return []
        
        passages = [{"id": c["chunk_id"], "text": c["text"]} for c in candidates]
        req = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(req)
        
        return [
            {"chunk_id": r["id"], "score": float(r["score"]), "text": r["text"]}
            for r in results[:top_k]
        ]
