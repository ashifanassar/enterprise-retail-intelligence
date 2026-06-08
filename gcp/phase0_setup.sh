#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-enterprise-retail-intelligence}"
REGION="${REGION:-us-central1}"
BQ_LOCATION="${BQ_LOCATION:-US}"
DATASET_ID="${DATASET_ID:-retail_mvp}"
BUCKET_NAME="${BUCKET_NAME:-retail-catalog-intake-${PROJECT_ID}}"
SERVICE_ACCOUNT_ID="${SERVICE_ACCOUNT_ID:-sa-retail-api}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project "${PROJECT_ID}"

gcloud services enable \
  bigquery.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  discoveryengine.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  dlp.googleapis.com \
  --project "${PROJECT_ID}"

bq --location="${BQ_LOCATION}" mk \
  --dataset \
  --description "Retail MVP Catalog" \
  "${PROJECT_ID}:${DATASET_ID}" || true

bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false "
CREATE TABLE IF NOT EXISTS \`${PROJECT_ID}.${DATASET_ID}.catalog_dim\` (
  sku_id STRING NOT NULL,
  title STRING,
  description STRING,
  category STRING,
  price FLOAT64,
  inventory_count INT64,
  brand STRING,
  image_url STRING
);"

bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false "
CREATE TABLE IF NOT EXISTS \`${PROJECT_ID}.${DATASET_ID}.search_logs\` (
  timestamp TIMESTAMP,
  session_id STRING,
  query STRING,
  results_count INT64,
  latency_ms INT64,
  dlp_triggered BOOL
);"

bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false "
CREATE TABLE IF NOT EXISTS \`${PROJECT_ID}.${DATASET_ID}.cart_events\` (
  event_id STRING,
  session_id STRING,
  event_type STRING,
  sku_id STRING,
  promo_code STRING,
  discount_pct FLOAT64,
  cart_total FLOAT64,
  risk_score FLOAT64,
  hitl_required BOOL,
  timestamp TIMESTAMP,
  status STRING
);"

gcloud storage buckets create "gs://${BUCKET_NAME}" \
  --project "${PROJECT_ID}" \
  --location "${REGION}" \
  --uniform-bucket-level-access || true

gcloud iam service-accounts create "${SERVICE_ACCOUNT_ID}" \
  --project "${PROJECT_ID}" \
  --display-name "Retail API Service Account" || true

gcloud firestore databases create \
  --project="${PROJECT_ID}" \
  --location="${REGION}" || true

gcloud pubsub topics create retail-hitl-escalations \
  --project="${PROJECT_ID}" || true

for role in \
  roles/discoveryengine.admin \
  roles/aiplatform.user \
  roles/datastore.user \
  roles/dlp.user \
  roles/pubsub.publisher \
  roles/bigquery.dataViewer \
  roles/bigquery.dataEditor \
  roles/bigquery.jobUser \
  roles/artifactregistry.reader \
  roles/logging.logWriter
do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role "${role}" \
    --quiet
done

echo "Phase 0 complete."
echo "Project: ${PROJECT_ID}"
echo "Bucket: gs://${BUCKET_NAME}"
echo "Service account: ${SERVICE_ACCOUNT_EMAIL}"