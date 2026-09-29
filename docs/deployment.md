# Deployment notes

The Bicep under `infrastructure/bicep/` is a skeleton for a later deployment. Do not treat it as a tested landing zone. Nothing in the MVP deploy scripts targets a subscription.

## Modules

| File | Resource |
| --- | --- |
| `main.bicep` | Wires the modules. Parameters only, no secret values |
| `storage.bicep` | Storage account, private blob access, TLS 1.2 |
| `openai.bicep` | Cognitive Services account, kind OpenAI |
| `document-intelligence.bicep` | Cognitive Services account, kind FormRecognizer |
| `search.bicep` | Azure AI Search |
| `cosmos.bicep` | Cosmos DB account, SQL API, database and container partitioned by `/ticket_id` |
| `keyvault.bicep` | Key Vault. Secret names are parameters. Values are not in source |
| `appservice.bicep` | Linux App Service for the API. Settings point at Key Vault references |

Create the OpenAI deployment and the Document Intelligence resource in the portal or a later module once names and capacity are chosen. The skeleton does not pick a model SKU that would start billing.

## Live mode

Install `backend/requirements-azure.txt` and set `USE_MOCK_AZURE=false`. Required variables are listed in `backend/.env.example`:

- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`, `AZURE_DOCUMENT_INTELLIGENCE_KEY`
- `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER`
- `AZURE_COSMOS_ENDPOINT`, `AZURE_COSMOS_KEY`, `AZURE_COSMOS_DATABASE`, `AZURE_COSMOS_CONTAINER`
- `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_KEY`, `AZURE_SEARCH_INDEX` optional. If search is empty, the API loads `audit_criteria.json`

The frontend build should set `VITE_API_BASE_URL` to the API origin. In local dev, leave it empty so Vite proxies `/api`.

CORS origins default to `http://127.0.0.1:43123` and `http://localhost:43123`.

## What a live call sends

Document Intelligence receives the PDF bytes. Azure OpenAI receives the system prompt, the criteria JSON, and the structured ticket fields listed in `IncidentTicket.llm_payload`. It does not receive the PDF. Blob storage receives the original PDF and nothing else. Cosmos receives the audit document, which includes the ticket snapshot needed to reproduce the review.

Put keys in Key Vault. The App Service skeleton uses `@Microsoft.KeyVault(...)` references instead of inline secrets.
