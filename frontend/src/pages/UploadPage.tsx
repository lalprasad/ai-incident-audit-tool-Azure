import { useState } from "react";
import { Button, Spinner } from "@fluentui/react-components";
import { Link } from "react-router-dom";

import { ErrorState } from "../components/States";
import { useJob } from "../hooks/useJob";
import { ApiError, request } from "../services/api";
import type { AuditJob } from "../types/audit";

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "working" | "ready">("idle");
  const [error, setError] = useState<string | null>(null);
  const [hot, setHot] = useState(false);
  const { job, error: pollError } = useJob(phase === "ready" ? jobId : null);

  const status = job?.status;
  const running = phase === "working" || (status !== undefined && status !== "Completed" && status !== "Failed" && status !== "Uploaded");

  async function loadSample() {
    setError(null);
    setPhase("working");
    try {
      const created = await request<AuditJob>("/api/audits/sample", { method: "POST" });
      setFile(null);
      setJobId(created.id);
      setPhase("idle");
    } catch (caught) {
      setPhase("idle");
      setError(caught instanceof ApiError ? caught.message : "The sample extract could not be loaded.");
    }
  }

  async function startAudit() {
    setError(null);
    setPhase("working");
    try {
      let id = jobId;
      if (file) {
        const body = new FormData();
        body.append("file", file);
        const created = await request<AuditJob>("/api/audits/upload", { method: "POST", body });
        id = created.id;
        setJobId(id);
      }
      if (!id) {
        setPhase("idle");
        setError("Choose a PDF or load the sample extract first.");
        return;
      }
      await request<AuditJob>(`/api/audits/${id}/process`, { method: "POST" });
      setPhase("ready");
    } catch (caught) {
      setPhase("idle");
      setError(caught instanceof ApiError ? caught.message : "The audit could not be started.");
    }
  }

  const visibleJob = job;
  const stages = visibleJob?.stages ?? ["Uploaded", "Extracting", "Tickets identified", "Auditing", "Completed"];
  const current = visibleJob?.status ?? (jobId ? "Uploaded" : null);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Audit a ServiceNow extract</h1>
          <p>
            Upload a PDF of one or more incidents. The audit scores user engagement, issue diagnosis, and solutioning from text in the ticket. The percentage is calculated here, not by the model.
          </p>
        </div>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {pollError ? <ErrorState message={pollError} /> : null}
      <section className="panel stack">
        <div
          className={hot ? "dropzone hot" : "dropzone"}
          onDragOver={(event) => {
            event.preventDefault();
            setHot(true);
          }}
          onDragLeave={() => setHot(false)}
          onDrop={(event) => {
            event.preventDefault();
            setHot(false);
            const next = event.dataTransfer.files?.[0];
            if (next) {
              setFile(next);
              setJobId(null);
              setPhase("idle");
            }
          }}
        >
          <strong>Drop a ServiceNow PDF</strong>
          <span className="muted">or choose a file. The sample extract contains eight incidents.</span>
          <div className="row" style={{ justifyContent: "center", marginTop: 12 }}>
            <input
              aria-label="ServiceNow PDF"
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => {
                const next = event.target.files?.[0] ?? null;
                setFile(next);
                setJobId(null);
                setPhase("idle");
              }}
            />
          </div>
        </div>
        <p className="muted">
          {file ? `Selected ${file.name}` : jobId ? "Sample extract is ready to audit." : "No file selected."}
        </p>
        <div className="row">
          <Button appearance="secondary" onClick={() => void loadSample()} disabled={phase === "working" || running}>
            Load sample extract
          </Button>
          <Button
            appearance="primary"
            onClick={() => void startAudit()}
            disabled={phase === "working" || running || (!file && !jobId)}
          >
            {phase === "working" ? "Starting audit" : "Start audit"}
          </Button>
          {running ? <Spinner size="tiny" label="Working through the extract" /> : null}
        </div>
      </section>
      {current ? (
        <section className="panel">
          <strong>Processing status</strong>
          <div className="stepper" aria-label="Audit stages">
            {stages.map((stage) => {
              const index = stages.indexOf(stage);
              const currentIndex = stages.indexOf(current === "Failed" ? "Completed" : current);
              const className =
                current === "Failed" && stage === "Completed"
                  ? "step bad"
                  : index < currentIndex
                    ? "step done"
                    : stage === current
                      ? "step current"
                      : "step";
              return (
                <span key={stage} className={className}>
                  {stage}
                </span>
              );
            })}
          </div>
          {visibleJob?.status === "Failed" ? (
            <p role="alert">{visibleJob.error || "The audit failed."}</p>
          ) : null}
          {visibleJob?.warnings?.length ? (
            <ul>
              {visibleJob.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : null}
          {visibleJob?.status === "Completed" ? (
            <div className="stack">
              <p>{visibleJob.ticket_ids.length} tickets scored.</p>
              <div className="row">
                <Link to="/dashboard">
                  <Button appearance="primary">Open dashboard</Button>
                </Link>
                {visibleJob.ticket_ids.map((ticketId) => (
                  <Link key={ticketId} to={`/tickets/${ticketId}`}>
                    {ticketId}
                  </Link>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
      <section className="panel">
        <strong>What gets scored</strong>
        <div className="kpi-grid" style={{ marginTop: 12 }}>
          <div>
            <div className="label">Engagement</div>
            <p className="muted">Timely, meaningful updates. Comment count alone does not decide the score.</p>
          </div>
          <div>
            <div className="label">Diagnosis</div>
            <p className="muted">What caused it, where, and why. A symptom is not a root cause.</p>
          </div>
          <div>
            <div className="label">Solutioning</div>
            <p className="muted">What changed, who did it, and how recovery was checked.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
