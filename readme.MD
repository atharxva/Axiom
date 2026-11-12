---
title: Axiom RAG - Enterprise Compliance & Document Verification
emoji: ⚖️
colorFrom: blue
colorTo: slate
sdk: docker
app_port: 7860
pinned: false
---

# Axiom RAG: Enterprise Hybrid Search & Document Compliance Engine

Axiom RAG is an enterprise-grade document compliance and verification engine. It pairs hybrid lexical (BM25) and dense semantic (ChromaDB) retrieval with cross-encoder neural reranking (FlashRank) and confidence gating to perform verified question answering over contracts, policies, and regulatory statutes.

## Architecture Highlights
- **Clause-Preserving Chunker**: Custom regex chunker isolating individual compliance articles.
- **Hybrid Retrieval**: Combines BM25Okapi with ChromaDB cosine vector search.
- **Reciprocal Rank Fusion (RRF)**: Merges rank positions with a smoothing parameter ($k=60$).
- **Cross-Encoder Reranking**: Sub-20ms neural reranking via TinyBERT ONNX.
- **Deterministic Confidence Gate**: Rejects unverified inquiries with confidence $< 0.50$.
- **Native PDF Citation View**: Interactive split-screen viewer jumping to the exact physical page and highlighting the referenced sentence.

## Environment Variables
- `GEMINI_API_KEY`: Google Gemini API key used by the executive synthesizer. (Set this in the Space Settings -> Variables and secrets).
