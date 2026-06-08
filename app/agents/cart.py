from datetime import datetime, timedelta, timezone

from google.cloud import firestore

from app.config import FIRESTORE_DATABASE, PROJECT_ID

db = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DATABASE)

def get_cart(session_id: str) -> dict:
    doc = db.collection("carts").document(session_id).get()

    if doc.exists:
        cart = doc.to_dict() or {}
        cart.setdefault("session_id", session_id)
        cart.setdefault("items", [])
        cart.setdefault("total", 0.0)
        cart.setdefault("promo_code", None)
        return cart

    return {
        "session_id": session_id,
        "items": [],
        "total": 0.0,
        "promo_code": None,
    }

def save_cart(session_id: str, cart: dict) -> None:
    cart["updated_at"] = datetime.now(timezone.utc)
    cart["expires_at"] = datetime.now(timezone.utc) + timedelta(hours=2)
    db.collection("carts").document(session_id).set(cart)

def _recalculate_total(cart: dict) -> None:
    subtotal = sum(
        float(item["price"]) * int(item["quantity"])
        for item in cart["items"]
    )
    discount_pct = float(cart.get("discount_pct", 0) or 0)

    cart["subtotal"] = subtotal
    cart["total"] = subtotal * (1 - discount_pct / 100)

def add_item(session_id: str, product: dict, quantity: int = 1) -> dict:
    cart = get_cart(session_id)

    for item in cart["items"]:
        if item["sku_id"] == product["sku_id"]:
            item["quantity"] += quantity
            _recalculate_total(cart)
            save_cart(session_id, cart)
            return cart

    cart["items"].append(
        {
            "sku_id": product["sku_id"],
            "title": product["title"],
            "price": float(product["price"]),
            "brand": product.get("brand"),
            "quantity": quantity,
        }
    )

    _recalculate_total(cart)
    save_cart(session_id, cart)
    return cart

def remove_item(session_id: str, sku_id: str) -> dict:
    cart = get_cart(session_id)
    cart["items"] = [
        item for item in cart["items"]
        if item["sku_id"] != sku_id
    ]

    _recalculate_total(cart)
    save_cart(session_id, cart)
    return cart

def apply_promo(session_id: str, promo_code: str) -> tuple[dict, float]:
    promo_codes = {
        "SAVE10": 10.0,
        "SAVE20": 20.0,
        "SAVE30": 30.0,
        "WELCOME": 15.0,
    }

    cart = get_cart(session_id)
    discount = promo_codes.get(promo_code.upper(), 0.0)

    if discount > 0:
        cart["promo_code"] = promo_code.upper()
        cart["discount_pct"] = discount
        _recalculate_total(cart)
        save_cart(session_id, cart)

    return cart, discount

def clear_cart(session_id: str) -> None:
    db.collection("carts").document(session_id).delete()