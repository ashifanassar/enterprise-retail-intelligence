Use this as your README.md.

# Enterprise Retail Intelligence

Retail AI commerce MVP built on Google Cloud. The platform demonstrates AI-powered product discovery, conversational commerce, cart transactions, policy enforcement, HITL review, SendGrid notifications, MCP review tools, API Gateway routing, and Firebase-hosted demo UIs.

## Architecture

```text
Firebase Hosting UI
        |
        v
API Gateway
        |
        v
Cloud Run FastAPI Backend
        |
        +--> Vertex AI Search for product discovery
        +--> Gemini 2.5 Flash for grounded responses
        +--> BigQuery for catalog/inventory grounding
        +--> Firestore for session memory, cart state, and HITL queue
        +--> Pub/Sub for HITL escalation events
        +--> SendGrid for HITL email notifications
        +--> MCP server for programmatic HITL review tools

Main Features
Semantic product search using Vertex AI Search
LangGraph multi-agent orchestration
Intent routing via Governor Agent
Product recommendation and grounded generation
Cart operations: add, remove, show cart, promo, checkout
Risk scoring for high-value checkout and discount actions
HITL policy enforcement for high-risk transactions
Firestore-backed HITL escalation queue
Admin UI for approve/reject review flow
Pub/Sub escalation publishing
SendGrid email notification support
MCP tools for HITL review automation
API Gateway as API front door
Firebase Hosting for public demo UI

**Agent Architecture**
Governor Agent
  -> Search Executor
      -> Generator Agent
  -> Transaction Executor
      -> Risk Engine
      -> Policy / HITL
  -> Chat Node
Key Endpoints
GET    /health
POST   /search
POST   /chat
POST   /agent
GET    /hitl/pending
GET    /hitl/config
GET    /hitl/{escalation_id}
POST   /hitl/{escalation_id}/approve
POST   /hitl/{escalation_id}/reject
DELETE /session/{session_id}

**Project Structure**
app/
  agents/
    cart.py
    chat_node.py
    generator.py
    governor.py
    graph.py
    hitl.py
    policy.py
    risk_engine.py
    search_executor.py
    state.py
    transaction_executor.py
  main.py
  search.py
  chat.py
  config.py
  auth.py

gcp/
  deploy_cloud_run.sh
  deploy_api_gateway.sh
  api_gateway_openapi.yaml.template
  phase0_setup.sh
  phase1_load_catalog.sh

mcp/
  hitl_review_server.py
  requirements.txt

docs/
  policies/mock-retail-policy-pack/

scripts/
  generate_catalog.py

retail-ai-demo.html
hitl-admin.html
Environment Variables
Create environment variables in Cloud Run or local .env.

GCP_PROJECT_ID=enterprise-retail-intelligence
GCP_LOCATION=global
VERTEX_SEARCH_ENGINE_ID=
VERTEX_SEARCH_DATASTORE_ID=
VERTEX_SEARCH_SERVING_CONFIG_ID=default_search
BQ_DATASET=retail_mvp

API_SECRET_KEY=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

FIRESTORE_DATABASE=default

HITL_REVIEWER_ROLE=demo-reviewer / retail ops admin
HITL_NOTIFICATION_CHANNEL=Pub/Sub + Firestore queue + SendGrid email
HITL_APPROVAL_SLA_HOURS=2
HITL_EMAIL_PROVIDER=SendGrid
HITL_REVIEWER_EMAIL=

SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=
SENDGRID_FROM_NAME=Retail AI HITL
Local Run
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
Health check:

curl http://localhost:8080/health
Deploy Cloud Run
cd ~/project9-RetailCommerce

export PROJECT_ID="enterprise-retail-intelligence"
export REGION="us-central1"

bash gcp/deploy_cloud_run.sh
For demo access:

gcloud run services add-iam-policy-binding retail-ai-api \
  --region="us-central1" \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --quiet
Deploy API Gateway
cd ~/project9-RetailCommerce

export PROJECT_ID="enterprise-retail-intelligence"
export REGION="us-central1"
export CLOUD_RUN_URL="https://retail-ai-api-1039944541778.us-central1.run.app"

bash gcp/deploy_api_gateway.sh
Deploy Firebase Hosting
mkdir -p public
cp retail-ai-demo.html public/
cp hitl-admin.html public/

firebase deploy --only hosting --project enterprise-retail-intell-b188a
Published demo:

https://retail-ai-demo-ashifa.web.app/retail-ai-demo.html
https://retail-ai-demo-ashifa.web.app/hitl-admin.html
HITL Flow
Customer checkout
  -> Transaction Executor
  -> Risk Engine
  -> risk_score >= 0.8
  -> Policy Node pauses action
  -> Firestore escalation created
  -> Pub/Sub event published
  -> SendGrid email attempted
  -> Admin UI approve/reject
MCP Tools
The MCP server exposes:

list_hitl_pending
get_hitl_request
approve_hitl_request
reject_hitl_request
Run MCP server:

cd mcp
pip install -r requirements.txt
python hitl_review_server.py
Security Notes
This is an MVP/demo implementation.

Do not commit .env or real secrets.
Use Secret Manager for production secrets.
Rotate exposed demo API keys after public demos.
Restrict Cloud Run access in production.
Add Cloud Armor / Load Balancer for enterprise edge security.
Use least-privilege IAM roles.
Current Status

**Completed:**

Cloud Run backend
Vertex AI Search integration
LangGraph multi-agent flow
Cart and transaction operations
HITL policy enforcement
Firestore HITL queue
Admin review UI
Pub/Sub escalation publishing
SendGrid integration path
MCP review tools
API Gateway
Firebase-hosted demo UI
Pending production hardening:

Secret Manager integration
Cloud Armor and HTTPS Load Balancer
Full HITL resume-after-approval workflow
Policy RAG over retail policy documents
Production IAM lockdown
Monitoring dashboards and alerts

LLM will be triggered on the below basis:
Example:
suggest me a red dress under 5000
Flow:
/agent
-> Governor Agent classifies intent = search
-> Search Executor retrieves products from Vertex AI Search
-> Generator Agent calls Gemini 2.5 Flash
-> Gemini generates a grounded recommendation

Policy RAG questions
Example:
What is your return policy?
Can I exchange an item?
How long does delivery take?
Flow:
/agent
-> Governor Agent classifies intent = policy_question
-> Policy RAG Node retrieves policy docs from Vertex AI Search
-> Gemini generates policy answer from retrieved context



**LLM Not Triggered**
/health
/search direct product retrieval
show my cart
add item to cart
remove item from cart
apply promo
checkout risk scoring
HITL approve/reject
/hitl/pending


**cache common policy answers:**
return policy
exchange policy
shipping policy
promo policy
