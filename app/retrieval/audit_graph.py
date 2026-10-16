from langgraph.graph import StateGraph, START, END
from app.retrieval.graph_state import AuditState
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.reranker import RerankerService
from app.retrieval.llm_service import LLMService

def build_audit_graph(hybrid: HybridSearcher, reranker: RerankerService, min_confidence: float = 0.50):
    llm = LLMService()

    def retrieve_node(state: AuditState) -> dict:
        candidates = hybrid.search(state["query"], top_k=10)
        ranked = reranker.rerank(state["query"], candidates, top_k=3)
        top_score = ranked[0]["score"] if ranked else 0.0
        return {"documents": ranked, "confidence_score": top_score}

    def evaluate_node(state: AuditState) -> dict:
        return {"is_sufficient": state["confidence_score"] >= min_confidence}

    def generate_node(state: AuditState) -> dict:
        top_doc = state["documents"][0]["text"]
        conversational_answer = llm.synthesize_audit_answer(state["query"], top_doc)
        return {"final_answer": conversational_answer}

    def fallback_node(state: AuditState) -> dict:
        top_doc = state["documents"][0]["text"] if state["documents"] else "No text found."
        ans = f"Audit Rejection (Low Confidence: {state['confidence_score']:.4f}). Closest matching excerpt:\n\n{top_doc}"
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
