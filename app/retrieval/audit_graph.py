from langgraph.graph import StateGraph, START, END
from app.retrieval.graph_state import AuditState
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.reranker import RerankerService

def build_audit_graph(hybrid: HybridSearcher, reranker: RerankerService, min_confidence: float = 0.50):
    def retrieve_node(state: AuditState) -> dict:
        candidates = hybrid.search(state["query"], top_k=4)
        ranked = reranker.rerank(state["query"], candidates, top_k=2)
        top_score = ranked[0]["score"] if ranked else 0.0
        return {"documents": ranked, "confidence_score": top_score}

    def evaluate_node(state: AuditState) -> dict:
        return {"is_sufficient": state["confidence_score"] >= min_confidence}

    def generate_node(state: AuditState) -> dict:
        top_doc = state["documents"][0]["text"]
        ans = f"Verified Audit Policy: Based on official compliance documentation:\n{top_doc}"
        return {"final_answer": ans}

    def fallback_node(state: AuditState) -> dict:
        ans = f"Audit Rejection: Confidence score ({state['confidence_score']:.4f}) below threshold ({min_confidence}). No verified policy found."
        return {"final_answer": ans}

    def route_decision(state: AuditState) -> str:
        return "generate" if state["is_sufficient"] else "fallback"

    workflow = StateGraph(AuditState)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("fallback", fallback_node)

    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "evaluate")
    workflow.add_conditional_edges("evaluate", route_decision, {"generate": "generate", "fallback": "fallback"})
    workflow.add_edge("generate", END)
    workflow.add_edge("fallback", END)

    return workflow.compile()
