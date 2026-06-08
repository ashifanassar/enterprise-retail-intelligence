from typing import Any, Literal, TypedDict

Intent = Literal["search", "transact", "casual_chat", "policy_question"]

class GraphState(TypedDict, total=False):
    query: str
    intent: Intent
    products: list[dict[str, Any]]
    response: str
    session_id: str
    history: list[dict[str, str]]
    latency_ms: int
    error: str | None
    hitl_required: bool | None
    risk_score: float | None
    risk_reasons: list[str]
    policy_status: str | None
    action: str | None
    cart: dict[str, Any]
    pii_detected: bool
    escalation_id: str | None