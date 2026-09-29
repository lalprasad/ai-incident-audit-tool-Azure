# API

Interactive schemas are served at `http://127.0.0.1:43124/docs` while the API is running. Routes below are the MVP set. Handlers validate input and call services. They do not score tickets themselves.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Process up, mock flag, criteria version |
| POST | `/api/audits/upload` | Multipart PDF. Returns a job in status Uploaded |
| POST | `/api/audits/sample` | Stores the bundled multi-ticket PDF as a new job |
| POST | `/api/audits/{job_id}/process` | Starts extraction and scoring. Poll the job for status |
| GET | `/api/audits/jobs` | Upload history |
| GET | `/api/audits/jobs/{job_id}` | One job, including warnings and stage timings |
| DELETE | `/api/audits/jobs/{job_id}` | Deletes the PDF and audits from that job |
| GET | `/api/audits` | Audit summaries, newest first, all versions |
| GET | `/api/audits/{audit_id}` | Full audit, ticket snapshot, measures, evidence |
| DELETE | `/api/audits/{audit_id}` | Deletes one audit document |
| GET | `/api/audits/export?format=csv\|xlsx` | Latest ticket per id by default. `latest_only=false` exports every version |
| GET | `/api/tickets/{ticket_id}` | Latest audit for that ticket |
| POST | `/api/tickets/{ticket_id}/review` | Body `{decision: accept\|comment, comments}`. Does not change scores |
| PUT | `/api/tickets/{ticket_id}/measures/{measure_id}` | Body `{auditor_score, auditor_comments, override_reason}`. Keeps `ai_score` |
| GET | `/api/dashboard/summary` | Aggregates for the latest version of each ticket, plus an executive summary |
| GET | `/api/criteria` | Rubric used by the engine and the model prompt |

Job statuses: Uploaded, Extracting, Tickets identified, Auditing, Completed, Failed.

A PDF that is not a PDF is rejected at upload. A readable PDF with no incident records completes as Failed and keeps the error on the job. A second process of a completed job returns 409. A failed job can be processed again; partial audits from that attempt are removed first.

## Export columns

Ticket ID, audit version, audited at, short description, priority, severity, state, assignment group, assigned to, opened at, resolved at, AI and final scores for the three measures, overall score, maximum, percentage, classification, human review, review reasons, auditor override, gaps, recommended actions, criteria version, prompt version, model version, and totals computed by.

The Excel file adds a Summary sheet with the executive summary. Cells that start with `=`, `+`, `-`, or `@` are prefixed so spreadsheet formulas are not executed.

The original brief referred to a column list that is not in this repository. The columns above are the ones this API writes.
