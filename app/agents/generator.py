from google import genai
from langsmith import traceable

from app.agents.state import GraphState
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.dlp import redact_pii
from app.model_armor import ModelArmorBlockedError, sanitize_model_response


SYSTEM_PROMPT = """You are a retail shopping assistant.
ABSOLUTE RULES:
1. ONLY recommend products from AVAILABLE PRODUCTS list
2. Never invent products not in the list
3. Never recommend OUT OF STOCK items
4. If nothing matches say: I don't have matching products for that request
5. Keep responses under 100 words"""


@traceable(name="Generator Agent")
def generator_node(state: GraphState) -> GraphState:
    products = state.get("products", [])

    if not products:
        return {
            **state,
            "response": "I don't have matching products in our current catalogue for that request.",
        }

    product_lines = []
    for product in products:
        product_lines.append(
            f"SKU {product.get('sku_id')}: {product.get('title')} | "
            f"Brand: {product.get('brand')} | Price: Rs.{float(product.get('price') or 0):.0f} | "
            f"Stock: AVAILABLE"
        )
    products_context = "\n".join(product_lines)

    if not GEMINI_API_KEY:
        first = products[0]
        return {
            **state,
            "response": (
                f"I found {len(products)} in-stock options. A strong match is "
                f"{first.get('title')} at Rs.{float(first.get('price') or 0):.0f}."
            ),
            "error": "GEMINI_API_KEY is not configured.",
        }

    prompt = f"""{SYSTEM_PROMPT}

Customer query: {state["query"]}

AVAILABLE PRODUCTS:
{products_context}

Respond helpfully using only the products above."""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        clean = sanitize_model_response(response.text or "")
        redacted, pii_detected = redact_pii(clean)
        return {**state, "response": redacted, "pii_detected": pii_detected}
    except ModelArmorBlockedError:
        return {**state, "response": "I cannot provide that response. Please rephrase your shopping request."}
    except Exception as exc:
        return {
            **state,
            "response": "I could not process your request. Please try again.",
            "error": str(exc),
        }
