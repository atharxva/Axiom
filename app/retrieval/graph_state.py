from typing import TypedDict, Any

class AuditState(TypedDict):
    query: str
    documents: list[dict[str, Any]]
    confidence_score: float
    is_sufficient: bool
    final_answer: str
