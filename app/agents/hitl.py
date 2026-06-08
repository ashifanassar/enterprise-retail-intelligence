import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from google.cloud import firestore, pubsub_v1

from app.config import (
    FIRESTORE_DATABASE,
    HITL_APPROVAL_SLA_HOURS,
    HITL_EMAIL_PROVIDER,
    HITL_NOTIFICATION_CHANNEL,
    HITL_REVIEWER_EMAIL,
    HITL_REVIEWER_ROLE,
    POLICY_RAG_SOURCE,
    PROJECT_ID,
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL,
    SENDGRID_FROM_NAME,
)


db = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DATABASE)
publisher = pubsub_v1.PublisherClient()
HITL_TOPIC = os.getenv("HITL_TOPIC", "retail-hitl-escalations")


def _send_sendgrid_email(payload: dict[str, Any]) -> str:
    if not (SENDGRID_API_KEY and SENDGRID_FROM_EMAIL and HITL_REVIEWER_EMAIL):
        return "not_configured"

    reviewer_emails = [
        email.strip()
        for email in HITL_REVIEWER_EMAIL.split(",")
        if email.strip()
    ]

    if not reviewer_emails:
        return "not_configured"

    subject = f"HITL review required: {payload['event_type']} risk={payload['risk_score']}"

    text = (
        "A retail transaction requires human review.\n\n"
        f"Escalation ID: {payload['escalation_id']}\n"
        f"Session ID: {payload['session_id']}\n"
        f"Action: {payload['event_type']}\n"
        f"Risk score: {payload['risk_score']}\n"
        f"Reasons: {', '.join(payload.get('reasons', []))}\n"
        f"Cart total: {payload.get('cart_total', 0)}\n"
        f"Item count: {payload.get('item_count', 0)}\n"
        f"Approval due at: {payload.get('approval_due_at')}\n\n"
        "Review this request in the HITL Admin Console or via MCP tools."
    )

    body = {
        "personalizations": [
            {
                "to": [{"email": email} for email in reviewer_emails],
            }
        ],
        "from": {
            "email": SENDGRID_FROM_EMAIL,
            "name": SENDGRID_FROM_NAME,
        },
        "subject": subject,
        "content": [
            {
                "type": "text/plain",
                "value": text,
            }
        ],
    }

    request = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return f"sent:{response.status}"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return f"failed:{exc.code}:{detail}"
    except Exception as exc:
        return f"failed:{type(exc).__name__}"


def create_hitl_escalation(
    session_id: str,
    event_type: str,
    risk_score: float,
    reasons: list[str],
    query: str,
    cart: dict[str, Any],
) -> str:
    escalation_id = str(uuid.uuid4())
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    due_at = (now_dt + timedelta(hours=HITL_APPROVAL_SLA_HOURS)).isoformat()

    payload = {
        "escalation_id": escalation_id,
        "session_id": session_id,
        "event_type": event_type,
        "risk_score": risk_score,
        "reasons": reasons,
        "query": query,
        "cart_total": cart.get("total", 0),
        "item_count": len(cart.get("items", [])),
        "status": "pending",
        "reviewer_role": HITL_REVIEWER_ROLE,
        "notification_channel": HITL_NOTIFICATION_CHANNEL,
        "approval_sla_hours": HITL_APPROVAL_SLA_HOURS,
        "approval_due_at": due_at,
        "email_provider": HITL_EMAIL_PROVIDER,
        "email_requested": bool(
            SENDGRID_API_KEY and SENDGRID_FROM_EMAIL and HITL_REVIEWER_EMAIL
        ),
        "policy_rag_source": POLICY_RAG_SOURCE,
        "created_at": now,
        "updated_at": now,
    }

    db.collection("hitl_escalations").document(escalation_id).set(payload)

    topic_path = publisher.topic_path(PROJECT_ID, HITL_TOPIC)
    publisher.publish(topic_path, json.dumps(payload).encode("utf-8"))

    email_status = _send_sendgrid_email(payload)
    db.collection("hitl_escalations").document(escalation_id).set(
        {
            "email_status": email_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        merge=True,
    )

    return escalation_id


def list_pending_escalations(limit: int = 20) -> list[dict[str, Any]]:
    query = (
        db.collection("hitl_escalations")
        .where("status", "==", "pending")
        .limit(limit)
    )

    return [
        {
            "id": doc.id,
            **(doc.to_dict() or {}),
        }
        for doc in query.stream()
    ]


def get_escalation(escalation_id: str) -> dict[str, Any]:
    snapshot = db.collection("hitl_escalations").document(escalation_id).get()

    if not snapshot.exists:
        raise KeyError(f"Escalation {escalation_id} not found")

    return {
        "id": snapshot.id,
        **(snapshot.to_dict() or {}),
    }


def hitl_operating_model() -> dict[str, Any]:
    sendgrid_configured = bool(
        SENDGRID_API_KEY and SENDGRID_FROM_EMAIL and HITL_REVIEWER_EMAIL
    )

    return {
        "reviewer": HITL_REVIEWER_ROLE,
        "notification": HITL_NOTIFICATION_CHANNEL,
        "approval_sla_hours": HITL_APPROVAL_SLA_HOURS,
        "rag_docs": POLICY_RAG_SOURCE,
        "email_provider": HITL_EMAIL_PROVIDER,
        "sendgrid_configured": sendgrid_configured,
        "sendgrid_from_email": SENDGRID_FROM_EMAIL or "not_configured",
        "sendgrid_from_name": SENDGRID_FROM_NAME,
        "reviewer_email": HITL_REVIEWER_EMAIL or "not_configured",
    }


def resolve_escalation(
    escalation_id: str,
    decision: str,
    reviewer: str = "demo-reviewer",
) -> dict[str, Any]:
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")

    ref = db.collection("hitl_escalations").document(escalation_id)
    snapshot = ref.get()

    if not snapshot.exists:
        raise KeyError(f"Escalation {escalation_id} not found")

    update = {
        "status": decision,
        "reviewer": reviewer,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    ref.set(update, merge=True)

    return {
        "id": escalation_id,
        **(snapshot.to_dict() or {}),
        **update,
    }