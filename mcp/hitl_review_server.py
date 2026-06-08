import json
import os
import urllib.error
import urllib.request
from typing import Any

from mcp.server.fastmcp import FastMCP


API_BASE = os.getenv("RETAIL_API_BASE", "https://retail-ai-api-1039944541778.us-central1.run.app")
API_KEY = os.getenv("RETAIL_API_KEY", "retail-ai-mvp-secret-2026")

mcp = FastMCP("retail-hitl-review")


def _request(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"API error {exc.code}: {detail}") from exc


@mcp.tool()
def list_hitl_pending() -> dict[str, Any]:
    """List pending HITL escalation requests."""
    return _request("/hitl/pending")


@mcp.tool()
def get_hitl_request(escalation_id: str) -> dict[str, Any]:
    """Get one HITL escalation request by ID."""
    return _request(f"/hitl/{escalation_id}")


@mcp.tool()
def approve_hitl_request(escalation_id: str, reviewer: str = "mcp-reviewer") -> dict[str, Any]:
    """Approve a pending HITL escalation request."""
    return _request(
        f"/hitl/{escalation_id}/approve",
        method="POST",
        body={"reviewer": reviewer},
    )


@mcp.tool()
def reject_hitl_request(escalation_id: str, reviewer: str = "mcp-reviewer") -> dict[str, Any]:
    """Reject a pending HITL escalation request."""
    return _request(
        f"/hitl/{escalation_id}/reject",
        method="POST",
        body={"reviewer": reviewer},
    )


if __name__ == "__main__":
    mcp.run()