# Security, cost, and roadmap

## Security

- No credentials are committed. `backend/.env.example` and `frontend/.env.example` contain empty values.
- `USE_MOCK_AZURE` defaults to true so a local run does not contact Azure.
- Upload names are not used as storage paths. Blob names are the job id plus `.pdf`.
- Path checks reject blob names that leave the data directory.
- Uploads over 20 MB are rejected. Non-PDF bytes are rejected before they are stored.
- Logs can include job id, ticket id, stage, status, duration, retry count, and token counts. They cannot include work notes, description, cause, resolution, prompts, or raw ticket text. The logger drops those keys if a caller passes them.
- The evidence checker removes quotes, timestamps, and page numbers that are not in the ticket.
- `DELETE /api/audits/{audit_id}` and `DELETE /api/audits/jobs/{job_id}` remove stored results and, for a job, the PDF. That is the MVP deletion path.
- There is no authentication in this MVP. Do not expose the API on a network where the tickets are confidential.
- The export prefixes cells that look like spreadsheet formulas.

## Cost

Mock mode does not call Azure.

A live ticket costs roughly:

- Document Intelligence: one layout analysis per uploaded PDF, billed by page.
- Azure OpenAI: one chat completion per ticket. The prompt includes the rubric and the structured ticket, not the PDF. Temperature is 0. Token usage is stored when the service returns it.
- Blob storage: the original PDF. Negligible next to the model calls.
- Cosmos DB: one document per audit version, plus the job document. Request units scale with how often the dashboard lists audits.
- Azure AI Search: unused unless an endpoint is configured. The MVP reads the local rubric either way.

Retries use exponential backoff and stop after three attempts. Invalid JSON is not retried.

## Roadmap

Not built in this pass:

- Entra ID or another sign-in, and per-team authorization
- A reviewed landing-zone deployment and a pipeline that publishes the Bicep
- A criteria editor in the UI
- Application Insights and Key Vault wiring beyond the skeleton
- A human-review queue with assignment and SLA
- Team, project, and service filters, or trend analytics beyond the current dashboard
- A consistency job that compares live model runs with `sample-data/evaluation-dataset.json`

The dashboard charts, override flow, and export are part of the MVP, not deferred analytics.
