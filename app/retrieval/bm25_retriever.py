import re
from rank_bm25 import BM25Okapi
from app.models.chunk import DocumentChunk

class BM25Retriever:
    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self.corpus_tokens = [self._tokenize(c.text) for c in chunks]
        self.bm25 = BM25Okapi(self.corpus_tokens)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def search(
        self, 
        query: str, 
        top_k: int = 2, 
        user_id: str | None = None, 
        doc_id: str | None = None
    ) -> list[tuple[DocumentChunk, float]]:
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        filtered_ranked: list[tuple[DocumentChunk, float]] = []
        for chunk, score in zip(self.chunks, scores):
            if user_id and chunk.metadata.user_id and chunk.metadata.user_id != user_id:
                continue
            if doc_id and chunk.metadata.doc_id and chunk.metadata.doc_id != doc_id:
                continue
            filtered_ranked.append((chunk, score))
            
        ranked = sorted(filtered_ranked, key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

