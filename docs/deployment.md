# Deployment (Azure AI)

The app runs in two modes:

| Mode | When | AI stack |
| --- | --- | --- |
| Mock | `USE_MOCK_AZURE=true` (default locally) | Deterministic rules + local files |
| Azure AI | `USE_MOCK_AZURE=false` | Azure OpenAI, Document Intelligence, Blob, Cosmos |

Live mode supports **API keys** or **managed identity** (`AZURE_USE_MANAGED_IDENTITY=true` with empty keys).

## Container layout

`Dockerfile` builds the React UI into `backend/static` and serves **API + SPA** from one FastAPI process (`SERVE_FRONTEND=true`). That image is what App Service runs.

## One-command deploy

Requirements: Azure CLI logged in (or service principal env vars), Docker.

```bash
export AZURE_SUBSCRIPTION_ID=...
export AZURE_LOCATION=eastus          # optional
export AZURE_RESOURCE_GROUP=rg-incaudit
export AZURE_NAME_PREFIX=incaudit

# Service principal (optional; otherwise az login)
export AZURE_TENANT_ID=...
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...

chmod +x scripts/deploy-azure.sh
./scripts/deploy-azure.sh
```

The script:

1. Creates a resource group and Azure Container Registry
2. Builds and pushes the Docker image
3. Deploys Bicep (OpenAI + gpt-4o-mini deployment, Document Intelligence, Storage, Cosmos, Key Vault, App Service)
4. Writes AI keys into Key Vault
5. Restarts the web app and probes `/api/health`

App settings use `@Microsoft.KeyVault(...)` references — secrets are not inlined in Bicep.

## Bicep modules

| File | Resource |
| --- | --- |
| `main.bicep` | Composition + Key Vault / Cognitive Services / Blob RBAC for the app identity |
| `openai.bicep` | Azure OpenAI account **and** chat model deployment |
| `document-intelligence.bicep` | Form Recognizer / Document Intelligence |
| `storage.bicep` | Storage account + `incident-audits` container |
| `cosmos.bicep` | Cosmos DB SQL API, partition `/ticket_id` |
| `keyvault.bicep` | RBAC-enabled vault |
| `appservice.bicep` | Linux container App Service |
| `search.bicep` | Optional Azure AI Search |

Default App Service auth uses **Key Vault secret references** for OpenAI, Document Intelligence, Storage, and Cosmos keys (`AZURE_USE_MANAGED_IDENTITY=false`). Bicep also grants the app **Cognitive Services User** and **Storage Blob Data Contributor** so you can switch to managed identity later without redeploying those resources.

## Live environment variables

See `backend/.env.example`. Required for Azure AI:

- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`
- `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT_URL`
- `AZURE_COSMOS_ENDPOINT`, `AZURE_COSMOS_DATABASE`, `AZURE_COSMOS_CONTAINER`
- Keys **or** managed identity

Optional: `AZURE_SEARCH_*` (otherwise `audit_criteria.json` is used).

## Frontend

Local Vite leaves `VITE_API_BASE_URL` empty and proxies `/api` to port 43124.

Production builds also leave the base empty so the browser calls same-origin `/api` on App Service.

## Cost note

Azure OpenAI, Document Intelligence (S0), Cosmos, and App Service B1 incur charges. Tear down with:

```bash
az group delete --name "$AZURE_RESOURCE_GROUP" --yes --no-wait
```
