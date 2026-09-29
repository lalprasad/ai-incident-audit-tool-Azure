# AI Based Incident Audit Tool

Audits the quality of ServiceNow incident extracts. Upload a PDF, score each ticket on three measures, and review the evidence behind every score.

The model does not own the result. It proposes a 1–5 score and quotes from the ticket. A deterministic scoring engine checks the range, drops quotes that are not in the ticket, and computes the total, percentage, and classification.

Local runs default to `USE_MOCK_AZURE=true`. Mock and live Azure clients implement the same interfaces. No Azure credentials are required for the UI or the tests.

## Scores

| Measure | Question |
| --- | --- |
| User engagement | Were investigation updates timely and meaningful? |
| Issue diagnosis | What caused it, where, and why? |
| Solutioning | What was done, who did it, and how was recovery checked? |

Each measure is 1–5. Scores 1 and 2 are system-defined extensions and are labeled in the UI. Total = sum of the three scores (weights are configurable). Percentage = total / maximum × 100, rounded in application code.

| Percentage | Classification |
| --- | --- |
| 90–100 | Excellent |
| 75–89 | Good |
| 60–74 | Fair |
| Below 60 | Needs Improvement |

## Run locally

Requirements: Python 3.12 and Node 22.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python sample-data/build_pdf.py

cd backend
../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 43124
```

In another shell:

```bash
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:43123](http://127.0.0.1:43123). The Vite server proxies `/api` to port 43124.

On the New audit page, choose **Load sample extract** and then **Start audit**. The sample PDF contains eight incidents.

Optional: set `AUDIT_STAGE_DELAY_MS=400` before starting the API if you want the status stepper to pause on each stage.

Copy `backend/.env.example` if you want a local env file. Secrets stay empty in mock mode. Live Azure settings are documented in `docs/deployment.md`. Install `backend/requirements-azure.txt` only when `USE_MOCK_AZURE=false`.

## Tests

```bash
.venv/bin/pytest
```

Tests use the mock clients, local files, and the sample extract. They do not call the network and do not need Azure credentials.

## Layout

- `backend/` FastAPI application, scoring engine, mock and Azure adapters
- `frontend/` React, TypeScript, Vite, Fluent UI
- `sample-data/` eight-ticket extract, PDF, and expected score ranges
- `infrastructure/bicep/` skeletons only — nothing is deployed from this repo
- `docs/` architecture, rubric, API, deployment, security, cost, and roadmap

## Sample incidents

| Ticket | What it demonstrates | Mock result |
| --- | --- | --- |
| INC1001 | Complete updates, cause, owner, and validation | 15/15 · 100% · Excellent |
| INC1002 | Regular updates, minor gaps, no formal validation | 12/15 · 80% · Good |
| INC1003 | Thin updates and a restart with no named owner | 9/15 · 60% · Fair |
| INC1004 | Closed with no notes, diagnosis, or resolution | 3/15 · 20% · Needs Improvement |
| INC1005 | Handling is present, but the text only says the pipeline failed | 10/15 · 66.67% · Fair |
| INC1006 | Cause and validation, but nobody is named as the actor | 11/15 · 73.33% · Fair |
| INC1007 | Cause and a named fix, with an empty work-note trail | 11/15 · 73.33% · Fair |
| INC1008 | Two different root-cause statements | 10/15 · 66.67% · Fair |

Assignment is not treated as ownership. A symptom is not treated as a root cause.
