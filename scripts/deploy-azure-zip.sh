#!/usr/bin/env bash
# Deploy without Docker: build SPA into backend/static and zip-deploy to App Service.
# Still creates Azure AI resources via Bicep (OpenAI, Document Intelligence, Storage, Cosmos, Key Vault).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCATION="${AZURE_LOCATION:-eastus}"
PREFIX="${AZURE_NAME_PREFIX:-incaudit}"
RG="${AZURE_RESOURCE_GROUP:-rg-${PREFIX}}"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}
need az
need npm
need python3

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

echo "==> Resource group $RG"
az group create --name "$RG" --location "$LOCATION" >/dev/null

# Placeholder image — zip path reconfigures the site to Python after Bicep.
PLACEHOLDER_IMAGE="mcr.microsoft.com/appsvc/staticsite:latest"
DEPLOY_NAME="incident-audit-zip-$(date +%Y%m%d%H%M%S)"

echo "==> Deploying infrastructure"
az deployment group create \
  --name "$DEPLOY_NAME" \
  --resource-group "$RG" \
  --template-file "$ROOT/infrastructure/bicep/main.bicep" \
  --parameters \
    namePrefix="$PREFIX" \
    dockerImage="$PLACEHOLDER_IMAGE" \
    openAiDeploymentName=gpt-4o-mini \
    openAiModelName=gpt-4o-mini \
  --query properties.outputs -o json > /tmp/incident-audit-outputs.json

APP_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['appName']['value'])")"
APP_URL="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['appUrl']['value'])")"
VAULT="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['vaultName']['value'])")"
OAI_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['openAiAccountName']['value'])")"
DI_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['documentAccountName']['value'])")"
ST_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['storageAccountName']['value'])")"
COSMOS_NAME="$(python3 -c "import json; print(json.load(open('/tmp/incident-audit-outputs.json'))['cosmosAccountName']['value'])")"

echo "==> Key Vault secrets"
OAI_KEY="$(az cognitiveservices account keys list -n "$OAI_NAME" -g "$RG" --query key1 -o tsv)"
DI_KEY="$(az cognitiveservices account keys list -n "$DI_NAME" -g "$RG" --query key1 -o tsv)"
ST_CONN="$(az storage account show-connection-string -n "$ST_NAME" -g "$RG" --query connectionString -o tsv)"
COSMOS_KEY="$(az cosmosdb keys list -n "$COSMOS_NAME" -g "$RG" --type keys --query primaryMasterKey -o tsv)"

# Grant current identity access to set secrets
PRINCIPAL="$(az ad signed-in-user show --query id -o tsv 2>/dev/null || az account show --query user.name -o tsv)"
KV_ID="$(az keyvault show -n "$VAULT" -g "$RG" --query id -o tsv)"
az role assignment create --role "Key Vault Secrets Officer" --assignee "$PRINCIPAL" --scope "$KV_ID" >/dev/null 2>&1 || true
sleep 15

az keyvault secret set --vault-name "$VAULT" --name openai-api-key --value "$OAI_KEY" >/dev/null
az keyvault secret set --vault-name "$VAULT" --name document-intelligence-key --value "$DI_KEY" >/dev/null
az keyvault secret set --vault-name "$VAULT" --name storage-connection-string --value "$ST_CONN" >/dev/null
az keyvault secret set --vault-name "$VAULT" --name cosmos-key --value "$COSMOS_KEY" >/dev/null

echo "==> Building frontend into backend/static"
(
  cd "$ROOT/frontend"
  npm ci
  VITE_API_BASE_URL= npm run build
  rm -rf "$ROOT/backend/static"
  mkdir -p "$ROOT/backend/static"
  cp -R dist/. "$ROOT/backend/static/"
)

echo "==> Switching App Service to Python 3.12 + zip deploy"
az webapp config set -g "$RG" -n "$APP_NAME" --linux-fx-version "PYTHON|3.12" >/dev/null
az webapp config appsettings set -g "$RG" -n "$APP_NAME" --settings \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  USE_MOCK_AZURE=false \
  SERVE_FRONTEND=true \
  AZURE_USE_MANAGED_IDENTITY=false \
  STARTUP_COMMAND="bash startup.sh" \
  >/dev/null

# Install azure deps during Oryx build
cat > "$ROOT/backend/requirements-deploy.txt" <<EOF
-r requirements.txt
-r requirements-azure.txt
EOF
# App Service looks for requirements.txt at project root of the zip
cp "$ROOT/backend/requirements.txt" /tmp/req-base.txt
cat "$ROOT/backend/requirements.txt" "$ROOT/backend/requirements-azure.txt" > "$ROOT/backend/requirements.txt"

ZIP="/tmp/incident-audit-app.zip"
rm -f "$ZIP"
(
  cd "$ROOT/backend"
  zip -qr "$ZIP" . -x '.data/*' -x '**/__pycache__/*' -x '.env' -x 'blobs/*'
)

# restore requirements.txt
cp /tmp/req-base.txt "$ROOT/backend/requirements.txt"

echo "==> Zip deploy"
az webapp deploy -g "$RG" -n "$APP_NAME" --src-path "$ZIP" --type zip >/dev/null
az webapp restart -g "$RG" -n "$APP_NAME" >/dev/null

echo "==> Health probe"
for i in $(seq 1 36); do
  if curl -fsS "${APP_URL}/api/health" >/tmp/health.json 2>/dev/null; then
    cat /tmp/health.json
    echo
    echo "Deployed: ${APP_URL}"
    exit 0
  fi
  sleep 10
done

echo "Deployed at ${APP_URL} but health did not pass yet." >&2
echo "${APP_URL}"
exit 1
