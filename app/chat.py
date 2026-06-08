import time
import uuid
from typing import Any

from google import genai
from google.cloud import firestore

from app.config import FIRESTORE_DATABASE, GEMINI_API_KEY, GEMINI_MODEL, PROJECT_ID
from app.dlp import redact_pii
from app.model_armor import ModelArmorBlockedError, sanitize_model_response
from app.search import search_products


db = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DATABASE)
genai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def delete_session(session_id: str) -> dict[str, str | bool]:
    session_ref = db.collection("sessions").document(session_id)
    existed = session_ref.get().exists
    session_ref.delete()
    return {"session_id": session_id, "deleted": True, "existed": existed}


def _product_context(products: list[dict[str, Any]]) -> str:
    lines = []
    for product in products[:8]:
        lines.append(
            f"- sku_id={product.get('sku_id')}; title={product.get('title')}; "
            f"price={product.get('price')}; inventory_count={product.get('inventory_count')}; "
            f"brand={product.get('brand')}; category={product.get('category')}"
        )

    return "\n".join(lines) if lines else "No in-stock products found."


def chat_response(query: str, session_id: str | None = None) -> dict[str, Any]:
    if genai_client is None:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    start = time.perf_counter()
    session_id = session_id or str(uuid.uuid4())

    session_ref = db.collection("sessions").document(session_id)
    session = session_ref.get()
    history = (session.to_dict() or {}).get("history", []) if session.exists else []

    search_result = search_products(query, session_id=session_id)

    prompt = f"""
You are a concise retail shopping assistant.

Rules:
- Recommend only products from the in-stock product context.
- Never recommend products with inventory_count equal to 0.
- Do not invent SKUs, prices, emails, phone numbers, or payment details.

Recent history:
{history[-6:]}

In-stock product context:
{_product_context(search_result["results"])}

User query:
{query}
"""

    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    try:
        armored = sanitize_model_response(response.text or "")
    except ModelArmorBlockedError:
        armored = "I cannot provide that response. Please rephrase your shopping request."

    redacted, pii_detected = redact_pii(armored)

    history.extend(
        [
            {"role": "user", "content": query},
            {"role": "assistant", "content": redacted},
        ]
    )

    session_ref.set(
        {"history": history[-20:], "updated_at": firestore.SERVER_TIMESTAMP},
        merge=True,
    )

    return {
        "session_id": session_id,
        "response": redacted,
        "pii_detected": pii_detected,
        "latency_ms": int((time.perf_counter() - start) * 1000),
    }
