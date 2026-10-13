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

    def search(self, query: str, top_k: int = 2) -> list[tuple[DocumentChunk, float]]:
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        ranked = sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
