from google import genai

from app.agents.state import GraphState
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.dlp import redact_pii
from app.model_armor import ModelArmorBlockedError, sanitize_model_response

SYSTEM_PROMPT = """You are a retail shopping assistant.
Rules:
1. ONLY recommend products from AVAILABLE PRODUCTS.
2. Never invent products.
3. Never recommend out-of-stock items.
4. Keep responses under 100 words."""

def generator_node(state: GraphState) -> GraphState:
    products = state.get("products", [])

    if not products:
        return {
            **state,
            "response": "I don't have matching products in our current catalogue for that request.",
        }

    products_context = "\n".join(
        f"SKU {p.get('sku_id')}: {p.get('title')} | "
        f"Brand: {p.get('brand')} | "
        f"Price: Rs.{float(p.get('price') or 0):.0f} | "
        f"Stock: AVAILABLE"
        for p in products
    )

    if not GEMINI_API_KEY:
        first = products[0]
        return {
            **state,
            "response": (
                f"I found {len(products)} in-stock options. "
                f"A strong match is {first.get('title')}."
            ),
        }

    prompt = f"""{SYSTEM_PROMPT}

Customer query: {state["query"]}

AVAILABLE PRODUCTS:
{products_context}

Respond helpfully using only the products above."""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
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
            "response": "I cannot provide that response. Please rephrase your shopping request.",
        }

    except Exception as exc:
        return {
            **state,
            "response": "I could not process your request. Please try again.",
            "error": str(exc),
        }