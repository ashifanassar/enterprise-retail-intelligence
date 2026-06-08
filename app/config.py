import os

from dotenv import load_dotenv


load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", os.getenv("PROJECT_ID", "retail-ai-mvp"))
LOCATION = os.getenv("GCP_LOCATION", os.getenv("LOCATION", "global"))
ENGINE_ID = os.getenv("VERTEX_SEARCH_ENGINE_ID", "retail-search-app_1778633921898")
DATA_STORE_ID = os.getenv("VERTEX_SEARCH_DATASTORE_ID", "retail-catalog-store")
SERVING_CONFIG_ID = os.getenv("VERTEX_SEARCH_SERVING_CONFIG_ID", "default_search")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BQ_DATASET = os.getenv("BQ_DATASET", "retail_mvp")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "retail-ai-mvp-secret-2026")
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "default")
HITL_REVIEWER_ROLE = os.getenv("HITL_REVIEWER_ROLE", "demo-reviewer / retail ops admin")
HITL_NOTIFICATION_CHANNEL = os.getenv("HITL_NOTIFICATION_CHANNEL", "Pub/Sub + Firestore queue")
HITL_APPROVAL_SLA_HOURS = int(os.getenv("HITL_APPROVAL_SLA_HOURS", "2"))
HITL_EMAIL_PROVIDER = os.getenv("HITL_EMAIL_PROVIDER", "TBD - SendGrid preferred if client has access")
POLICY_RAG_SOURCE = os.getenv("POLICY_RAG_SOURCE", "docs/policies/mock-retail-policy-pack")
API_VERSION = "1.0.0"
MODEL_ARMOR_LOCATION = os.getenv("MODEL_ARMOR_LOCATION", "us-central1")
MODEL_ARMOR_TEMPLATE_ID = os.getenv("MODEL_ARMOR_TEMPLATE_ID", "")
HITL_EMAIL_PROVIDER = os.getenv("HITL_EMAIL_PROVIDER", "SendGrid")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "Retail AI HITL")
HITL_REVIEWER_EMAIL = os.getenv("HITL_REVIEWER_EMAIL", "")