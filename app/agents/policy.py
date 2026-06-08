from app.agents.hitl import create_hitl_escalation
from app.agents.state import GraphState
from app.dlp import redact_pii


HITL_THRESHOLD = 0.8


def policy_node(state: GraphState) -> GraphState:
    risk_score = float(state.get("risk_score") or 0)
    risk_reasons = state.get("risk_reasons", [])
    action = state.get("action") or "unknown"

    if risk_score < HITL_THRESHOLD:
        return {
            **state,
            "hitl_required": False,
            "policy_status": "approved",
        }

    escalation_id = create_hitl_escalation(
        session_id=state["session_id"],
        event_type=action,
        risk_score=risk_score,
        reasons=risk_reasons,
        query=state["query"],
        cart=state.get("cart", {}),
    )
    response = (
        "This action requires human review before it can continue. "
        f"Escalation ID: {escalation_id}."
    )
    response, pii_detected = redact_pii(response)

    return {
        **state,
        "response": response,
        "hitl_required": True,
        "policy_status": "paused_for_review",
        "escalation_id": escalation_id,
        "pii_detected": pii_detected,
    }