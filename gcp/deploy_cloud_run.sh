#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-enterprise-retail-intelligence}"
REGION="${REGION:-us-central1}"
APP_LOCATION="${APP_LOCATION:-global}"
ENGINE_ID="${ENGINE_ID:-retail-commerce_1778777043423}"
DATA_STORE_ID="${DATA_STORE_ID:-retail-commerce_1778730532218}"
SERVING_CONFIG_ID="${SERVING_CONFIG_ID:-default_search}"
MODEL_ARMOR_LOCATION="${MODEL_ARMOR_LOCATION:-us-central1}"
MODEL_ARMOR_TEMPLATE_ID="${MODEL_ARMOR_TEMPLATE_ID:-}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-sa-retail-api@${PROJECT_ID}.iam.gserviceaccount.com}"
REPOSITORY="${REPOSITORY:-retail-ai-repo}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/retail-ai-api:${IMAGE_TAG:-v1}"
API_SECRET_KEY="${API_SECRET_KEY:-retail-ai-mvp-secret-2026}"

gcloud artifacts repositories create "${REPOSITORY}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Cloud Run images for Retail AI API" \
  --project="${PROJECT_ID}" || true

gcloud builds submit . \
  --tag="${IMAGE}" \
  --project="${PROJECT_ID}"

gcloud run deploy retail-ai-api \
  --image="${IMAGE}" \
  --platform=managed \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --min-instances=0 \
  --max-instances=3 \
  --memory=512Mi \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_LOCATION=${APP_LOCATION},VERTEX_SEARCH_ENGINE_ID=${ENGINE_ID},VERTEX_SEARCH_DATASTORE_ID=${DATA_STORE_ID},VERTEX_SEARCH_SERVING_CONFIG_ID=${SERVING_CONFIG_ID},BQ_DATASET=retail_mvp,API_SECRET_KEY=${API_SECRET_KEY},MODEL_ARMOR_LOCATION=${MODEL_ARMOR_LOCATION},MODEL_ARMOR_TEMPLATE_ID=${MODEL_ARMOR_TEMPLATE_ID}" \
  --no-allow-unauthenticated
