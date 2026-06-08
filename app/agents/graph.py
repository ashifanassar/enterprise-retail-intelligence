import uuid
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.chat_node import chat_node
from app.agents.generator import generator_node
from app.agents.governor import governor_node
from app.agents.search_executor import search_executor_node
from app.agents.state import GraphState
from app.agents.transaction_executor import transaction_executor_node
from app.agents.policy import policy_node

def route_intent(state: GraphState) -> str:
    intent = state.get("intent", "casual_chat")

    if intent == "search":
        return "search_executor"

    if intent == "transact":
        return "transaction_executor"

    return "chat_node"

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("governor", governor_node)
    graph.add_node("search_executor", search_executor_node)
    graph.add_node("generator", generator_node)
    graph.add_node("chat_node", chat_node)
    graph.add_node("transaction_executor", transaction_executor_node)
    graph.add_node("policy", policy_node)

    graph.set_entry_point("governor")

    graph.add_conditional_edges(
        "governor",
        route_intent,
        {
            "search_executor": "search_executor",
            "chat_node": "chat_node",
            "transaction_executor": "transaction_executor",
        },
    )

    graph.add_edge("search_executor", "generator")
    graph.add_edge("generator", END)
    graph.add_edge("chat_node", END)
    graph.add_edge("transaction_executor", END)
    graph.add_edge("transaction_executor", "policy")
    graph.add_edge("policy", END)

    return graph.compile()

retail_graph = build_graph()

def agent_response(query: str, session_id: str | None = None) -> dict[str, Any]:
    final_state = retail_graph.invoke(
        {
            "query": query,
            "session_id": session_id or str(uuid.uuid4()),
            "products": [],
            "history": [],
            "latency_ms": 0,
            "error": None,
            "hitl_required": False,
            "risk_score": 0.0,
            "risk_reasons": [],
            "policy_status": None,
            "pii_detected": False,
        }
    )

    return {
        "session_id": final_state["session_id"],
        "intent": final_state.get("intent"),
        "response": final_state.get("response"),
        "products": final_state.get("products", []),
        "action": final_state.get("action"),
        "cart": final_state.get("cart"),
        "risk_score": final_state.get("risk_score", 0),
        "risk_reasons": final_state.get("risk_reasons", []),
        "hitl_required": final_state.get("hitl_required", False),
        "policy_status": final_state.get("policy_status"),

        "escalation_id": final_state.get("escalation_id"),
        "pii_detected": final_state.get("pii_detected", False),
        "latency_ms": final_state.get("latency_ms", 0),
        "error": final_state.get("error"),
    }