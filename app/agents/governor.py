from google import genai

from app.agents.state import GraphState, Intent
from app.config import GEMINI_API_KEY, GEMINI_MODEL

TRANSACTION_CONTEXT = [
    "to cart", "from cart", "my cart", "show cart", "view cart",
    "promo", "coupon", "discount code", "checkout", "order now", "buy now",
]

POLICY_KEYWORDS = [
    "return", "refund", "delivery", "shipping", "policy",
    "exchange", "cancel", "warranty",
]

SEARCH_KEYWORDS = [
    "show me", "find", "search", "looking for", "want", "need",
    "dress", "top", "jacket", "shoes", "shirt", "trouser",
    "outfit", "wear", "suggest", "recommend", "under", "budget",
    "brand", "colour", "color", "size", "available",
]

def classify_intent_keywords(query: str) -> Intent | None:
    q = query.lower().strip()

    if any(k in q for k in TRANSACTION_CONTEXT) or "cart" in q:
        return "transact"

    if any(k in q for k in POLICY_KEYWORDS):
        return "policy_question"

    if any(k in q for k in SEARCH_KEYWORDS):
        return "search"

    if any(k in q for k in ["hi", "hello", "thanks", "thank you", "who are you"]):
        return "casual_chat"

    return None

def classify_intent_gemini(query: str) -> Intent:
    if not GEMINI_API_KEY:
        return "casual_chat"

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""Classify this retail customer query into exactly one category:
- search
- transact
- casual_chat
- policy_question

Query: "{query}"

Reply with only the category name."""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        intent = (response.text or "").strip().lower()

        if intent in ["search", "transact", "casual_chat", "policy_question"]:
            return intent  # type: ignore[return-value]

    except Exception:
        pass

    return "casual_chat"

def governor_node(state: GraphState) -> GraphState:
    intent = classify_intent_keywords(state["query"]) or classify_intent_gemini(state["query"])
    return {**state, "intent": intent}