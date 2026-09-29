import { useState } from "react";
import { Badge, Button, Field, Select, Textarea } from "@fluentui/react-components";

import type { Evidence, Measure } from "../types/audit";

export function MeasureCard({
  measure,
  busy,
  onEvidence,
  onOverride,
}: {
  measure: Measure;
  busy: boolean;
  onEvidence: (evidence: Evidence) => void;
  onOverride: (score: number, comments: string, reason: string) => Promise<void>;
}) {
  const [score, setScore] = useState(String(measure.auditor_score ?? measure.final_score));
  const [comments, setComments] = useState(measure.auditor_comments ?? "");
  const [reason, setReason] = useState(measure.override_reason ?? "");
  const [localError, setLocalError] = useState<string | null>(null);

  return (
    <article className="panel measure">
      <header>
        <div>
          <strong>{measure.measure_name}</strong>
          <div className="row" style={{ marginTop: 6 }}>
            <Badge appearance="tint" color={measure.confidence >= 0.85 ? "success" : measure.confidence >= 0.7 ? "informative" : "warning"}>
              {measure.confidence_label} · {measure.confidence.toFixed(2)}
            </Badge>
            {measure.overridden ? (
              <Badge appearance="tint" color="important">
                Auditor override
              </Badge>
            ) : null}
          </div>
        </div>
        <div className="score-pair">
          <div>
            <strong>
              {measure.ai_score}
              {measure.ai_score_is_system_extension ? "*" : ""}
            </strong>
            <span>AI score</span>
          </div>
          <div>
            <strong>
              {measure.final_score}
              {measure.final_score_is_system_extension ? "*" : ""}
            </strong>
            <span>Final score</span>
          </div>
        </div>
      </header>
      {measure.ai_score_is_system_extension || measure.final_score_is_system_extension ? (
        <p className="muted">
          * Scores 1 and 2 are system-defined extensions of the 3–5 rubric. They mark severe gaps and stay visible to the auditor.
        </p>
      ) : null}
      <p className="muted">{measure.guidance}</p>
      <div>
        <strong>Evidence</strong>
        <div className="stack" style={{ marginTop: 8 }}>
          {measure.evidence.map((item, index) => (
            <button
              key={`${item.ticket_field}-${index}`}
              type="button"
              className="evidence-btn"
              onClick={() => onEvidence(item)}
            >
              <q>{item.text}</q>
              <span className="muted">
                {item.evidence_status} · {item.ticket_field}
                {item.page ? ` · page ${item.page}` : ""}
              </span>
            </button>
          ))}
        </div>
      </div>
      {measure.strengths.length ? (
        <p>
          <strong>Strengths. </strong>
          {measure.strengths.join(" ")}
        </p>
      ) : null}
      {measure.gaps.length ? (
        <p>
          <strong>Gaps. </strong>
          {measure.gaps.join(" ")}
        </p>
      ) : null}
      <p>
        <strong>Recommendation. </strong>
        {measure.recommendation}
      </p>
      <form
        className="stack"
        onSubmit={(event) => {
          event.preventDefault();
          if (!reason.trim()) {
            setLocalError("Enter a reason so the original AI score stays explainable.");
            return;
          }
          setLocalError(null);
          void onOverride(Number(score), comments.trim(), reason.trim());
        }}
      >
        <Field label="Auditor score" orientation="horizontal">
          <Select value={score} onChange={(_, data) => setScore(data.value)}>
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={String(value)}>
                {value}
                {value <= 2 ? " — system-defined extension" : ""}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Auditor comments">
          <Textarea value={comments} onChange={(_, data) => setComments(data.value)} rows={2} />
        </Field>
        <Field label="Override reason" required>
          <Textarea value={reason} onChange={(_, data) => setReason(data.value)} rows={2} />
        </Field>
        {localError ? <p role="alert">{localError}</p> : null}
        <Button appearance="primary" type="submit" disabled={busy}>
          {busy ? "Saving override" : "Save override"}
        </Button>
      </form>
    </article>
  );
}
