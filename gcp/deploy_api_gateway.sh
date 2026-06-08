#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-enterprise-retail-intelligence}"
REGION="${REGION:-us-central1}"
CLOUD_RUN_URL="${CLOUD_RUN_URL:-https://retail-ai-api-1039944541778.us-central1.run.app}"
API_ID="${API_ID:-retail-ai-platform-api}"
GATEWAY_ID="${GATEWAY_ID:-retail-ai-platform-gateway}"
CONFIG_ID="${CONFIG_ID:-retail-ai-platform-config-$(date +%Y%m%d%H%M%S)}"
SPEC_TEMPLATE="${SPEC_TEMPLATE:-gcp/api_gateway_openapi.yaml.template}"
SPEC_RENDERED="${SPEC_RENDERED:-gcp/api_gateway_openapi.yaml}"

gcloud services enable \
  apigateway.googleapis.com \
  servicemanagement.googleapis.com \
  servicecontrol.googleapis.com \
  --project="${PROJECT_ID}"

sed "s|__CLOUD_RUN_URL__|${CLOUD_RUN_URL}|g" "${SPEC_TEMPLATE}" > "${SPEC_RENDERED}"

gcloud api-gateway apis create "${API_ID}" \
  --project="${PROJECT_ID}" || true

gcloud api-gateway api-configs create "${CONFIG_ID}" \
  --api="${API_ID}" \
  --openapi-spec="${SPEC_RENDERED}" \
  --project="${PROJECT_ID}"

if gcloud api-gateway gateways describe "${GATEWAY_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud api-gateway gateways update "${GATEWAY_ID}" \
    --api="${API_ID}" \
    --api-config="${CONFIG_ID}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}"
else
  gcloud api-gateway gateways create "${GATEWAY_ID}" \
    --api="${API_ID}" \
    --api-config="${CONFIG_ID}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}"
fi

GATEWAY_HOSTNAME="$(gcloud api-gateway gateways describe "${GATEWAY_ID}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --format='value(defaultHostname)')"

echo
echo "API Gateway deployed:"
echo "https://${GATEWAY_HOSTNAME}"
echo
echo "Test:"
echo "curl -i https://${GATEWAY_HOSTNAME}/health"