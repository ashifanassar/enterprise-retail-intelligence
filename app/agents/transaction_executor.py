import uuid
from datetime import datetime, timezone

from google.cloud import bigquery

from app.agents.cart import add_item, apply_promo, get_cart, remove_item
from app.agents.risk_engine import calculate_risk_score
from app.agents.state import GraphState
from app.config import BQ_DATASET, PROJECT_ID
from app.dlp import redact_pii
from app.search import search_products


bigquery_client = bigquery.Client(project=PROJECT_ID)

TRANSACTION_KEYWORDS = {
    "add": ["add", "put", "place", "include"],
    "remove": ["remove", "delete", "take out"],
    "promo": ["promo", "coupon", "discount", "code", "offer"],
    "checkout": ["checkout", "pay", "buy now", "order"],
    "view": ["show cart", "my cart", "view cart", "what's in"],
}


def detect_transaction_type(query: str) -> str:
    q = query.lower()

    for action, keywords in TRANSACTION_KEYWORDS.items():
        if any(keyword in q for keyword in keywords):
            return action

    return "view"


def extract_product_from_query(query: str, session_id: str) -> list[dict]:
    clean = query.lower()

    for word in [
        "add", "put", "place", "to cart", "to my cart",
        "remove", "delete", "from cart", "please", "can you",
    ]:
        clean = clean.replace(word, "").strip()

    if not clean:
        return []

    result = search_products(clean, session_id=session_id)
    return result["results"][:3]


def log_cart_event(
    session_id: str,
    event_type: str,
    cart: dict,
    risk_score: float,
    hitl: bool,
    sku_id: str = "",
    promo: str = "",
    discount: float = 0.0,
) -> None:
    rows = [
        {
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": event_type,
            "sku_id": sku_id,
            "promo_code": promo,
            "discount_pct": discount,
            "cart_total": cart.get("total", 0),
            "risk_score": risk_score,
            "hitl_required": hitl,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "blocked" if hitl else "approved",
        }
    ]

    try:
        bigquery_client.insert_rows_json(
            f"{PROJECT_ID}.{BQ_DATASET}.cart_events",
            rows,
        )
    except Exception:
        pass


def transaction_executor_node(state: GraphState) -> GraphState:
    query = state["query"]
    session_id = state["session_id"]
    event_type = detect_transaction_type(query)

    cart = get_cart(session_id)
    products = state.get("products", [])

    risk_score = 0.0
    hitl = False
    reasons: list[str] = []
    discount_pct = 0.0

    try:
        if event_type == "add":
            products = products or extract_product_from_query(query, session_id)

            if not products:
                response = (
                    "I couldn't find that product in our catalogue. "
                    "Please search for it first."
                )

            else:
                product = products[0]
                cart = add_item(session_id, product)
                risk_score, hitl, reasons = calculate_risk_score(cart, "add")

                if hitl:
                    response = "Your cart action is pending policy review."
                else:
                    response = (
                        f"Added '{product['title']}' to your cart. "
                        f"Cart total: Rs.{cart['total']:.0f}."
                    )

                log_cart_event(
                    session_id,
                    "add",
                    cart,
                    risk_score,
                    hitl,
                    product["sku_id"],
                )

        elif event_type == "remove":
            if cart["items"]:
                sku_id = cart["items"][0]["sku_id"]
                title = cart["items"][0]["title"]

                cart = remove_item(session_id, sku_id)

                response = (
                    f"Removed '{title}' from cart. "
                    f"Cart total: Rs.{cart['total']:.0f}."
                )

            else:
                response = "Your cart is already empty."

            risk_score, hitl, reasons = calculate_risk_score(cart, "remove")

            log_cart_event(
                session_id,
                "remove",
                cart,
                risk_score,
                hitl,
            )

        elif event_type == "promo":
            promo_codes = ["SAVE10", "SAVE20", "SAVE30", "WELCOME"]

            code = next(
                (
                    word
                    for word in query.upper().split()
                    if word in promo_codes
                ),
                None,
            )

            if not code:
                response = (
                    "Please provide a valid promo code: "
                    "SAVE10, SAVE20, SAVE30, or WELCOME."
                )

            else:
                cart, discount_pct = apply_promo(session_id, code)
                risk_score, hitl, reasons = calculate_risk_score(
                    cart,
                    "promo",
                    discount_pct,
                )

                if hitl:
                    response = "Your promo request is pending policy review."
                else:
                    response = (
                        f"Promo code {code} applied. "
                        f"New cart total: Rs.{cart['total']:.0f}."
                    )

                log_cart_event(
                    session_id,
                    "promo",
                    cart,
                    risk_score,
                    hitl,
                    promo=code,
                    discount=discount_pct,
                )

        elif event_type == "checkout":
            if not cart["items"]:
                response = "Your cart is empty. Add products before checking out."

            else:
                risk_score, hitl, reasons = calculate_risk_score(
                    cart,
                    "checkout",
                    cart.get("discount_pct", 0),
                )

                if hitl:
                    response = "Your checkout is pending policy review."
                else:
                    response = (
                        f"Order confirmed. Total: Rs.{cart['total']:.0f}. "
                        "Delivery in 3-5 business days."
                    )

                log_cart_event(
                    session_id,
                    "checkout",
                    cart,
                    risk_score,
                    hitl,
                )

        else:
            if cart["items"]:
                items_text = "\n".join(
                    f"- {item['title']} x{item['quantity']} = "
                    f"Rs.{item['price'] * item['quantity']:.0f}"
                    for item in cart["items"]
                )

                response = (
                    f"Your cart:\n{items_text}\n"
                    f"Total: Rs.{cart['total']:.0f}"
                )

            else:
                response = "Your cart is empty. Search for products to add."

    except Exception as exc:
        return {
            **state,
            "response": "I could not process that cart action. Please try again.",
            "error": str(exc),
            "intent": "transact",
        }

    response, pii_detected = redact_pii(response)

    return {
        **state,
        "response": response,
        "intent": "transact",
        "products": products,
        "cart": cart,
        "hitl_required": hitl,
        "risk_score": risk_score,
        "risk_reasons": reasons,
        "action": event_type,
        "pii_detected": pii_detected,
        "escalation_id": None,
    }