from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agents.graph import agent_response
from app.agents.hitl import list_pending_escalations, resolve_escalation
from app.auth import validate_api_key
from app.chat import chat_response, delete_session
from app.config import API_VERSION, PROJECT_ID
from app.search import search_products
from app.agents.hitl import list_pending_escalations, resolve_escalation
from app.agents.hitl import hitl_operating_model, list_pending_escalations, resolve_escalation
from fastapi import Depends, FastAPI

from app.agents.hitl import hitl_operating_model, list_pending_escalations, resolve_escalation
from app.agents.hitl import (
    get_escalation,
    hitl_operating_model,
    list_pending_escalations,
    resolve_escalation,
)
app = FastAPI(title="Retail AI MVP", version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: str | None = None


class HitlDecisionRequest(BaseModel):
    reviewer: str = "demo-reviewer"


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": API_VERSION,
        "project": PROJECT_ID,
    }



@app.post("/search")
def search(
    request: SearchRequest,
    _: str = Depends(validate_api_key),
) -> dict:
    return search_products(request.query, session_id=request.session_id)


@app.post("/chat")
def chat(
    request: SearchRequest,
    _: str = Depends(validate_api_key),
) -> dict:
    return chat_response(request.query, session_id=request.session_id)


@app.post("/agent")
def agent(
    request: SearchRequest,
    _: str = Depends(validate_api_key),
) -> dict:
    return agent_response(request.query, session_id=request.session_id)


@app.get("/hitl/pending")
def hitl_pending(_: str = Depends(validate_api_key)) -> dict:
    return {"items": list_pending_escalations()}


@app.get("/hitl/config")
def hitl_config(_: str = Depends(validate_api_key)) -> dict:
    return hitl_operating_model()


@app.get("/hitl/{escalation_id}")
def hitl_get(
    escalation_id: str,
    _: str = Depends(validate_api_key),
) -> dict:
    try:
        return get_escalation(escalation_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Escalation not found")


@app.post("/hitl/{escalation_id}/approve")
def hitl_approve(
    escalation_id: str,
    request: HitlDecisionRequest,
    _: str = Depends(validate_api_key),
) -> dict:
    try:
        return resolve_escalation(escalation_id, "approved", reviewer=request.reviewer)
    except KeyError:
        raise HTTPException(status_code=404, detail="Escalation not found")


@app.post("/hitl/{escalation_id}/reject")
def hitl_reject(
    escalation_id: str,
    request: HitlDecisionRequest,
    _: str = Depends(validate_api_key),
) -> dict:
    try:
        return resolve_escalation(escalation_id, "rejected", reviewer=request.reviewer)
    except KeyError:
        raise HTTPException(status_code=404, detail="Escalation not found")


@app.delete("/session/{session_id}")
def erase_session(
    session_id: str,
    _: str = Depends(validate_api_key),
) -> dict:
    return delete_session(session_id)