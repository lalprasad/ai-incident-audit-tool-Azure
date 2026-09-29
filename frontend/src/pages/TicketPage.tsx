import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Field, Textarea } from "@fluentui/react-components";
import { Link, useParams } from "react-router-dom";

import { EvidenceDialog } from "../components/EvidenceDialog";
import { MeasureCard } from "../components/MeasureCard";
import { ErrorState, LoadingState } from "../components/States";
import { ApiError, request } from "../services/api";
import type { AuditRecord, Evidence } from "../types/audit";
import { badgeColor, formatPercent, formatScore, formatWhen } from "../utils/format";

export function TicketPage() {
  const { ticketId = "" } = useParams();
  const [audit, setAudit] = useState<AuditRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [comments, setComments] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = await request<AuditRecord>(`/api/tickets/${ticketId}`);
      setAudit(body);
      setComments(body.auditor_review?.comments ?? "");
    } catch (caught) {
      setAudit(null);
      setError(caught instanceof ApiError ? caught.message : "The ticket could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function override(measureId: string, score: number, auditorComments: string, reason: string) {
    setBusyId(measureId);
    setSaveError(null);
    try {
      const updated = await request<AuditRecord>(`/api/tickets/${ticketId}/measures/${measureId}`, {
        method: "PUT",
        body: JSON.stringify({
          auditor_score: score,
          auditor_comments: auditorComments,
          override_reason: reason,
        }),
      });
      setAudit(updated);
    } catch (caught) {
      setSaveError(caught instanceof ApiError ? caught.message : "The override could not be saved.");
    } finally {
      setBusyId(null);
    }
  }

  async function accept() {
    setBusyId("review");
    setSaveError(null);
    try {
      const updated = await request<AuditRecord>(`/api/tickets/${ticketId}/review`, {
        method: "POST",
        body: JSON.stringify({ decision: "accept", comments }),
      });
      setAudit(updated);
    } catch (caught) {
      setSaveError(caught instanceof ApiError ? caught.message : "The review could not be saved.");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <LoadingState label="Loading ticket audit" />;
  if (error || !audit) return <ErrorState message={error || "Ticket was not found."} onRetry={() => void load()} />;

  const ticket = audit.ticket;
  const facts: [string, string][] = [
    ["State", ticket.state || "Not recorded"],
    ["Priority", ticket.priority || "Not recorded"],
    ["Severity", ticket.severity || "Not recorded"],
    ["Assignment group", ticket.assignment_group || "Not recorded"],
    ["Assigned to", ticket.assigned_to || "Not recorded"],
    ["Caller", ticket.caller || "Not recorded"],
    ["Service", ticket.business_service || "Not recorded"],
    ["Configuration item", ticket.configuration_item || "Not recorded"],
    ["Opened", formatWhen(ticket.opened_at)],
    ["Resolved", formatWhen(ticket.resolved_at)],
    ["Resolution code", ticket.resolution_code || "Not recorded"],
  ];

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <Link to="/dashboard" className="muted">
            Back to dashboard
          </Link>
          <h1>{audit.ticket_id}</h1>
          <p>{ticket.short_description || "No short description was extracted."}</p>
        </div>
        <div className="row">
          <Badge appearance="tint" color={badgeColor(audit.classification)} size="large">
            {audit.classification}
          </Badge>
          <strong>
            {formatScore(audit.overall_score)} / {formatScore(audit.maximum_score)} · {formatPercent(audit.percentage)}
          </strong>
        </div>
      </div>
      {saveError ? <ErrorState message={saveError} /> : null}
      <section className="split">
        <article className="panel">
          <strong>Ticket</strong>
          <dl className="facts" style={{ marginTop: 12 }}>
            {facts.map(([label, value]) => (
              <span key={label} style={{ display: "contents" }}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </span>
            ))}
          </dl>
        </article>
        <article className="panel stack">
          <div className="row">
            <strong>AI audit summary</strong>
            {audit.human_review_required ? (
              <Badge appearance="tint" color="warning">
                Human review
              </Badge>
            ) : (
              <Badge appearance="tint" color="success">
                No review flag
              </Badge>
            )}
            {audit.auditor_override ? (
              <Badge appearance="tint" color="important">
                Overridden
              </Badge>
            ) : null}
          </div>
          {audit.review_reasons.length ? (
            <p className="muted">Flags: {audit.review_reasons.join(", ")}.</p>
          ) : (
            <p className="muted">No insufficient-evidence, conflict, or confidence flags.</p>
          )}
          {audit.overall_gaps.length ? <p>{audit.overall_gaps.join(" ")}</p> : <p>No gaps were recorded.</p>}
          {audit.recommended_actions.length ? (
            <ul>
              {audit.recommended_actions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          ) : null}
          <p className="footer-note">
            Version {audit.audit_version} · {audit.ai_model} · criteria {audit.criteria_version}. Percentage is owned by the scoring engine.
          </p>
          <Field label="Auditor comments">
            <Textarea value={comments} onChange={(_, data) => setComments(data.value)} rows={3} />
          </Field>
          <Button appearance="secondary" disabled={busyId !== null} onClick={() => void accept()}>
            Accept AI scores
          </Button>
        </article>
      </section>
      <section className="split">
        <article className="panel">
          <strong>Cause and resolution</strong>
          <p>{ticket.cause || "Cause was not documented."}</p>
          <p>{ticket.resolution_notes || "Resolution notes were not documented."}</p>
          <p className="muted">{ticket.description || "Description was not documented."}</p>
        </article>
        <article className="panel">
          <strong>Investigation timeline</strong>
          {ticket.timeline.length ? (
            <ol className="timeline">
              {ticket.timeline.map((event, index) => (
                <li key={`${event.timestamp}-${index}`}>
                  <div>
                    <time>{formatWhen(event.timestamp)}</time> · <em>{event.event_type}</em> · {event.audience}
                  </div>
                  <div>
                    {event.author ? `${event.author}: ` : ""}
                    {event.text}
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="muted">No work notes or comments were extracted. Absence of updates is not treated as completed communication.</p>
          )}
        </article>
      </section>
      <section className="measure-grid">
        {audit.measures.map((measure) => (
          <MeasureCard
            key={measure.measure_id}
            measure={measure}
            busy={busyId === measure.measure_id}
            onEvidence={setEvidence}
            onOverride={(score, auditorComments, reason) => override(measure.measure_id, score, auditorComments, reason)}
          />
        ))}
      </section>
      <EvidenceDialog evidence={evidence} onClose={() => setEvidence(null)} />
    </div>
  );
}
