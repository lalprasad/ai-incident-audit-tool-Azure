import { Badge, Button, Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle } from "@fluentui/react-components";

import type { Evidence } from "../types/audit";
import { formatWhen } from "../utils/format";

export function EvidenceDialog({
  evidence,
  onClose,
}: {
  evidence: Evidence | null;
  onClose: () => void;
}) {
  return (
    <Dialog open={evidence !== null} onOpenChange={(_, data) => !data.open && onClose()}>
      <DialogSurface>
        <DialogBody>
          <DialogTitle>Ticket evidence</DialogTitle>
          <DialogContent>
            {evidence ? (
              <div className="stack">
                <Badge appearance="tint" color={evidence.evidence_status === "Supported" ? "success" : "warning"}>
                  {evidence.evidence_status}
                </Badge>
                <blockquote className="quote">{evidence.text}</blockquote>
                <dl className="facts">
                  <dt>Field</dt>
                  <dd>{evidence.ticket_field}</dd>
                  <dt>Section</dt>
                  <dd>{evidence.source_section}</dd>
                  <dt>Page</dt>
                  <dd>{evidence.page ?? "Not recorded"}</dd>
                  <dt>Timestamp</dt>
                  <dd>{formatWhen(evidence.timestamp)}</dd>
                  <dt>Relevance</dt>
                  <dd>{evidence.relevance}</dd>
                </dl>
                <p className="muted">
                  Supported quotes are copied from the ticket. Insufficient evidence means the record does not contain that fact. Missing information is not treated as completed work.
                </p>
              </div>
            ) : null}
          </DialogContent>
          <DialogActions>
            <Button appearance="secondary" onClick={onClose}>
              Close
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}
