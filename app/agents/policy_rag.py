import requests
import google.auth
from google.auth.transport.requests import Request
from google import genai
from langsmith import traceable

from app.agents.state import GraphState
from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    PROJECT_ID,
    POLICY_RAG_DATASTORE_ID,
    POLICY_RAG_LOCATION,
    POLICY_RAG_SERVING_CONFIG_ID,
)


def get_access_token() -> str:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(Request())
    return credentials.token


@traceable(name="Policy RAG Retrieval")
def retrieve_policy_context(query: str, page_size: int = 5) -> list[dict]:
    if not POLICY_RAG_DATASTORE_ID:
        return []

    access_token = get_access_token()
    url = (
        "https://discoveryengine.googleapis.com/v1/"
        f"projects/{PROJECT_ID}/locations/{POLICY_RAG_LOCATION}/"
        f"collections/default_collection/dataStores/{POLICY_RAG_DATASTORE_ID}/"
        f"servingConfigs/{POLICY_RAG_SERVING_CONFIG_ID}:search"
    )

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={"query": query, "pageSize": page_size},
        timeout=20,
    )
    response.raise_for_status()

    docs = []
    for result in response.json().get("results", []):
        document = result.get("document", {})
        derived = document.get("derivedStructData", {})
        docs.append(
            {
                "id": document.get("id"),
                "name": document.get("name"),
                "title": derived.get("title"),
                "link": derived.get("link"),
                "derived": derived,
                "rank_signals": result.get("rankSignals", {}),
            }
        )

    return docs


@traceable(name="Policy RAG Node")
def policy_rag_node(state: GraphState) -> GraphState:
    query = state["query"]
    policy_docs = retrieve_policy_context(query)

    if not policy_docs:
        return {
            **state,
            "response": "I could not find a matching policy document for that question.",
            "products": [],
            "action": "policy_answer",
            "policy_sources": [],
        }

    context = "\n\n".join(str(doc) for doc in policy_docs)
    prompt = f"""
You are a retail policy assistant.

Answer the customer question using only the policy context below.
If the answer is not in the policy context, say that the policy does not specify it.

Customer question:
{query}

Policy context:
{context}
"""

    if not GEMINI_API_KEY:
        return {
            **state,
            "response": f"Policy context found, but Gemini is not configured. Retrieved context: {context[:1000]}",
            "products": [],
            "action": "policy_answer",
            "policy_sources": policy_docs,
        }

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        answer = response.text or "No policy answer generated."
    except Exception as exc:
        answer = (
            "I found relevant policy information from the policy RAG data store, "
            "but Gemini generation is currently unavailable. "
            f"Reason: {type(exc).__name__}. "
            f"Retrieved policy context: {context[:1200]}"
        )

    return {
        **state,
        "response": answer,
        "products": [],
        "action": "policy_answer",
        "policy_sources": policy_docs,
    }
