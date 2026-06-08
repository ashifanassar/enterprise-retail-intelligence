from google import genai

from app.agents.state import GraphState
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.dlp import redact_pii
from app.model_armor import ModelArmorBlockedError, sanitize_model_response

CASUAL_PROMPT = """You are a friendly retail shopping assistant.
Answer briefly. Do not recommend specific products unless asked."""

POLICY_PROMPT = """You are a retail customer service assistant.
Standard policies:
- Returns: 30 days with receipt
- Delivery: 3-5 business days
- Refunds: processed in 5-7 business days
- Exchange: available within 30 days
Keep responses under 80 words."""

def chat_node(state: GraphState) -> GraphState:
    if not GEMINI_API_KEY:
        return {
            **state,
            "response": "I am here to help. Please ask me about products, cart actions, or policies.",
        }

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        system = POLICY_PROMPT if state.get("intent") == "policy_question" else CASUAL_PROMPT

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{system}\n\nCustomer: {state['query']}",
        )

        clean = sanitize_model_response(response.text or "")
        redacted, pii_detected = redact_pii(clean)

        return {
            **state,
            "response": redacted,
            "pii_detected": pii_detected,
        }

    except ModelArmorBlockedError:
        return {
            **state,
            "response": "I cannot provide that response. Please rephrase your request.",
        }

    except Exception as exc:
        return {
            **state,
            "response": "I am here to help. Please ask me about our products.",
            "error": str(exc),
        }