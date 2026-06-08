def calculate_risk_score(cart: dict, event_type: str, discount_pct: float = 0.0) -> tuple[float, bool, list[str]]:
    risk = 0.0
    reasons = []
    cart_total = float(cart.get("total", 0) or 0)

    if cart_total > 10000:
        risk += 0.4
        reasons.append(f"High cart value: Rs.{cart_total:.0f}")
    elif cart_total > 5000:
        risk += 0.2
        reasons.append(f"Medium cart value: Rs.{cart_total:.0f}")

    if discount_pct > 20:
        risk += 0.4
        reasons.append(f"Large discount: {discount_pct}%")
    elif discount_pct > 10:
        risk += 0.2
        reasons.append(f"Moderate discount: {discount_pct}%")

    for item in cart.get("items", []):
        if int(item.get("quantity", 1) or 1) > 5:
            risk += 0.3
            reasons.append(f"Bulk order: {item['quantity']}x {item['title']}")

    if event_type == "checkout" and discount_pct > 0 and cart_total > 5000:
        risk += 0.2
        reasons.append("Checkout with promo on high-value cart")

    risk = min(round(risk, 2), 1.0)
    return risk, risk >= 0.8, reasons