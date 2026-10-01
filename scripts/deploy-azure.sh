#!/usr/bin/env bash
# Deploy Incident Audit to Azure AI + App Service.
# Requires: az CLI logged in (service principal or user), Docker.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCATION="${AZURE_LOCATION:-eastus}"
PREFIX="${AZURE_NAME_PREFIX:-incaudit}"
RG="${AZURE_RESOURCE_GROUP:-rg-${PREFIX}}"
ACR_NAME="${AZURE_ACR_NAME:-${PREFIX}acr${RANDOM}}"
IMAGE_NAME="${AZURE_IMAGE_NAME:-incident-audit}"
IMAGE_TAG="${AZURE_IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

need az
need docker

if ! az account show >/dev/null 2>&1; then
  if [[ -n "${AZURE_CLIENT_ID:-}" && -n "${AZURE_CLIENT_SECRET:-}" && -n "${AZURE_TENANT_ID:-}" ]]; then
    az login --service-principal \
      -u "$AZURE_CLIENT_ID" \
      -p "$AZURE_CLIENT_SECRET" \
      --tenant "$AZURE_TENANT_ID" >/dev/null
  else
    echo "Not logged into Azure. Set AZURE_CLIENT_ID/SECRET/TENANT_ID or run az login." >&2
    exit 1
  fi
fi

if [[ -n "${AZURE_SUBSCRIPTION_ID:-}" ]]; then
  az account set --subscription "$AZURE_SUBSCRIPTION_ID"
fi

echo "==> Subscription: $(az account show --query id -o tsv)"
echo "==> Resource group: $RG ($LOCATION)"

az group create --name "$RG" --location "$LOCATION" >/dev/null

# ACR (names must be alphanumeric)
ACR_NAME="$(echo "$ACR_NAME" | tr -cd 'a-z0-9' | cut -c1-50)"
if ! az acr show -n "$ACR_NAME" -g "$RG" >/dev/null 2>&1; then
  echo "==> Creating ACR $ACR_NAME"
  az acr create -n "$ACR_NAME" -g "$RG" --sku Basic --admin-enabled true >/dev/null
fi

ACR_LOGIN_SERVER="$(az acr show -n "$ACR_NAME" -g "$RG" --query loginServer -o tsv)"
ACR_USER="$(az acr credential show -n "$ACR_NAME" -g "$RG" --query username -o tsv)"
ACR_PASS="$(az acr credential show -n "$ACR_NAME" -g "$RG" --query passwords[0].value -o tsv)"
IMAGE_REF="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "==> Building image $IMAGE_REF"
az acr login -n "$ACR_NAME" >/dev/null
docker build -t "$IMAGE_REF" "$ROOT"
docker push "$IMAGE_REF"

echo "==> Deploying Bicep"
DEPLOY_NAME="incident-audit-${IMAGE_TAG}"
az deployment group create \
  --name "$DEPLOY_NAME" \
  --resource-group "$RG" \
  --template-file "$ROOT/infrastructure/bicep/main.bicep" \
  --parameters \
    namePrefix="$PREFIX" \
    dockerImage="$IMAGE_REF" \
    acrLoginServer="https://${ACR_LOGIN_SERVER}" \
    acrUsername="$ACR_USER" \
    acrPassword="$ACR_PASS" \
    openAiDeploymentName=gpt-4o-mini \
    openAiModelName=gpt-4o-mini \
  --query properties.outputs -o json > /tmp/incident-audit-outputs.json

APP_URL="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['appUrl']['value'])")"
VAULT="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['vaultName']['value'])")"
OAI_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['openAiAccountName']['value'])")"
DI_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['documentAccountName']['value'])")"
ST_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['storageAccountName']['value'])")"
COSMOS_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['cosmosAccountName']['value'])")"

echo "==> Writing Key Vault secrets"
OAI_KEY="$(az cognitiveservices account keys list -n "$OAI_NAME" -g "$RG" --query key1 -o tsv)"
DI_KEY="$(az cognitiveservices account keys list -n "$DI_NAME" -g "$RG" --query key1 -o tsv)"
ST_CONN="$(az storage account show-connection-string -n "$ST_NAME" -g "$RG" --query connectionString -o tsv)"
COSMOS_KEY="$(az cosmosdb keys list -n "$COSMOS_NAME" -g "$RG" --type keys --query primaryMasterKey -o tsv)"

az keyvault secret set --vault-name "$VAULT" --name openai-api-key --value "$OAI_KEY" >/dev/null
az keyvault secret set --vault-name "$VAULT" --name document-intelligence-key --value "$DI_KEY" >/dev/null
az keyvault secret set --vault-name "$VAULT" --name storage-connection-string --value "$ST_CONN" >/dev/null
az keyvault secret set --vault-name "$VAULT" --name cosmos-key --value "$COSMOS_KEY" >/dev/null

# Key Vault may deny the current principal until RBAC propagates; grant the deployer Secrets Officer
DEPLOYER_OID="$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)"
if [[ -n "$DEPLOYER_OID" ]]; then
  az role assignment create \
    --role "Key Vault Secrets Officer" \
    --assignee-object-id "$DEPLOYER_OID" \
    --assignee-principal-type User \
    --scope "$(az keyvault show -n "$VAULT" -g "$RG" --query id -o tsv)" >/dev/null 2>&1 || true
fi

APP_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['appName']['value'])")"
echo "==> Restarting App Service $APP_NAME"
az webapp restart -n "$APP_NAME" -g "$RG" >/dev/null

echo "==> Waiting for health"
for i in $(seq 1 30); do
  if curl -fsS "${APP_URL}/api/health" >/tmp/health.json 2>/dev/null; then
    cat /tmp/health.json
    echo
    echo "Deployed: ${APP_URL}"
    exit 0
  fi
  sleep 10
done

echo "App deployed at ${APP_URL} but health check did not pass yet. Check Log stream." >&2
echo "${APP_URL}"
exit 1
