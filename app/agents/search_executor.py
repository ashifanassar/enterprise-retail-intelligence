from app.agents.state import GraphState
from app.search import search_products

def search_executor_node(state: GraphState) -> GraphState:
    try:
        result = search_products(state["query"], session_id=state.get("session_id"))
        return {
            **state,
            "session_id": result["session_id"],
            "products": result["results"],
            "latency_ms": result["latency_ms"],
            "error": None,
        }
    except Exception as exc:
        return {**state, "products": [], "error": str(exc)}