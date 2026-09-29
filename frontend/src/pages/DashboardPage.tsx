import { useCallback, useEffect, useState } from "react";
import { Badge, Button } from "@fluentui/react-components";
import { Link } from "react-router-dom";

import { HorizontalBars, ScoreBars, TrendChart } from "../components/Charts";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { ApiError, download, request } from "../services/api";
import type { AuditSummary, DashboardSummary } from "../types/audit";
import { badgeColor, barColor, formatPercent, formatScore, formatWhen } from "../utils/format";

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [audits, setAudits] = useState<AuditSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [exportError, setExportError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dash, list] = await Promise.all([
        request<DashboardSummary>("/api/dashboard/summary"),
        request<{ items: AuditSummary[] }>("/api/audits"),
      ]);
      setSummary(dash);
      const latest = new Map<string, AuditSummary>();
      for (const item of list.items) {
        const current = latest.get(item.ticket_id);
        if (!current || item.audit_version >= current.audit_version) latest.set(item.ticket_id, item);
      }
      setAudits([...latest.values()]);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The dashboard could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function exportReport(format: "csv" | "xlsx") {
    setExportError(null);
    try {
      await download(
        `/api/audits/export?format=${format}`,
        format === "csv" ? "incident-audit.csv" : "incident-audit.xlsx",
      );
    } catch (caught) {
      setExportError(caught instanceof ApiError ? caught.message : "Export failed.");
    }
  }

  if (loading) return <LoadingState label="Loading audit results" />;
  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!summary || summary.empty) {
    return (
      <EmptyState
        title="No audits yet"
        body="Upload a ServiceNow extract to score ticket quality. The sample file has eight incidents, including missing RCA, missing owner, missing updates, and conflicting notes."
        action={{ to: "/", label: "Start an audit" }}
      />
    );
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Audit dashboard</h1>
          <p>{summary.executive_summary}</p>
        </div>
        <div className="row">
          <Button appearance="secondary" onClick={() => void exportReport("csv")}>
            Export CSV
          </Button>
          <Button appearance="primary" onClick={() => void exportReport("xlsx")}>
            Export Excel
          </Button>
        </div>
      </div>
      {exportError ? <ErrorState message={exportError} /> : null}
      <section className="kpi-grid">
        <article className="panel kpi">
          <div className="label">Tickets</div>
          <div className="value">{summary.total_tickets}</div>
          <div className="hint">Latest version of each ticket</div>
        </article>
        <article className="panel kpi">
          <div className="label">Average score</div>
          <div className="value">
            {formatScore(summary.average_score)}
            <span style={{ fontSize: 16, color: "#5b7082" }}> / {formatScore(summary.maximum_score)}</span>
          </div>
          <div className="hint">{formatPercent(summary.average_percentage)}</div>
        </article>
        <article className="panel kpi">
          <div className="label">Human review</div>
          <div className="value">{summary.human_review_count}</div>
          <div className="hint">Low confidence, conflicts, or missing facts</div>
        </article>
        <article className="panel kpi">
          <div className="label">Criteria</div>
          <div className="value" style={{ fontSize: 22 }}>{summary.criteria_version}</div>
          <div className="hint">Totals from {summary.totals_computed_by.replaceAll("_", " ")}</div>
        </article>
      </section>
      <section className="chart-grid">
        <article className="panel">
          <strong>Quality distribution</strong>
          <HorizontalBars
            items={summary.quality_distribution.map((item) => ({
              label: item.label,
              value: item.count,
              color: barColor(item.label),
            }))}
          />
        </article>
        <article className="panel">
          <strong>Measure averages</strong>
          <HorizontalBars
            max={5}
            items={summary.measure_averages.map((item) => ({
              label: item.measure_name.replace(" & Investigation Handling", ""),
              value: item.average,
              color: "#0f6cbd",
            }))}
          />
        </article>
        <article className="panel">
          <strong>Score distribution</strong>
          <ScoreBars items={summary.score_distribution} />
        </article>
        <article className="panel">
          <strong>Trend by open date</strong>
          <TrendChart points={summary.score_trend} />
        </article>
      </section>
      <section className="chart-grid">
        <article className="panel">
          <strong>Common gaps</strong>
          {summary.common_gaps.length ? (
            <ul className="gap-list">
              {summary.common_gaps.map((gap) => (
                <li key={gap.text}>
                  <span>{gap.text}</span>
                  <strong>{gap.count}</strong>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No gaps were recorded.</p>
          )}
        </article>
        <article className="panel">
          <strong>Review reasons</strong>
          {summary.review_reason_counts.length ? (
            <ul className="gap-list">
              {summary.review_reason_counts.map((reason) => (
                <li key={reason.label}>
                  <span>{reason.label}</span>
                  <strong>{reason.count}</strong>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No tickets currently require human review.</p>
          )}
        </article>
      </section>
      <section className="panel" style={{ overflowX: "auto" }}>
        <table className="results">
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Summary</th>
              <th>Score</th>
              <th>Class</th>
              <th>Review</th>
              <th>Opened</th>
            </tr>
          </thead>
          <tbody>
            {audits.map((audit) => (
              <tr key={audit.id}>
                <td data-label="Ticket">
                  <Link to={`/tickets/${audit.ticket_id}`}>{audit.ticket_id}</Link>
                  <div className="muted">v{audit.audit_version}</div>
                </td>
                <td data-label="Summary">{audit.short_description || "No short description"}</td>
                <td data-label="Score">
                  {formatScore(audit.overall_score)} / {formatScore(audit.maximum_score)}
                  <div className="muted">{formatPercent(audit.percentage)}</div>
                </td>
                <td data-label="Class">
                  <Badge appearance="tint" color={badgeColor(audit.classification)}>
                    {audit.classification}
                  </Badge>
                </td>
                <td data-label="Review">{audit.human_review_required ? "Needs review" : "Clear"}</td>
                <td data-label="Opened">{formatWhen(audit.opened_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <p className="footer-note">
        Percentage is total score divided by the maximum, computed in application code. Model totals are discarded.
      </p>
    </div>
  );
}
