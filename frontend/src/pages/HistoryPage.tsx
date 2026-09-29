import { useCallback, useEffect, useState } from "react";
import { Button, Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle } from "@fluentui/react-components";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { ApiError, request } from "../services/api";
import type { AuditJob } from "../types/audit";
import { formatWhen } from "../utils/format";

export function HistoryPage() {
  const [jobs, setJobs] = useState<AuditJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<AuditJob | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = await request<{ items: AuditJob[] }>("/api/audits/jobs");
      setJobs(body.items);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Job history could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function remove(job: AuditJob) {
    try {
      await request(`/api/audits/jobs/${job.id}`, { method: "DELETE" });
      setPendingDelete(null);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The job could not be deleted.");
    }
  }

  if (loading) return <LoadingState label="Loading audit history" />;
  if (error && !jobs.length) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!jobs.length) {
    return (
      <EmptyState
        title="No extracts uploaded"
        body="Jobs appear here after you upload a PDF or load the sample extract."
        action={{ to: "/", label: "Upload an extract" }}
      />
    );
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Audit history</h1>
          <p>Each upload is kept until you delete it. Deleting a job removes its stored PDF and the audits created from it.</p>
        </div>
      </div>
      {error ? <ErrorState message={error} /> : null}
      <section className="panel" style={{ overflowX: "auto" }}>
        <table className="results">
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Tickets</th>
              <th>Uploaded</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td data-label="File">{job.filename}</td>
                <td data-label="Status">
                  {job.status}
                  {job.error ? <div className="muted">{job.error}</div> : null}
                </td>
                <td data-label="Tickets">
                  {job.ticket_ids.length
                    ? job.ticket_ids.map((ticketId) => (
                        <div key={ticketId}>
                          <Link to={`/tickets/${ticketId}`}>{ticketId}</Link>
                        </div>
                      ))
                    : "—"}
                </td>
                <td data-label="Uploaded">{formatWhen(job.created_at)}</td>
                <td data-label="Actions">
                  <Button appearance="subtle" onClick={() => setPendingDelete(job)}>
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <Dialog open={pendingDelete !== null} onOpenChange={(_, data) => !data.open && setPendingDelete(null)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>Delete this audit job?</DialogTitle>
            <DialogContent>
              This removes the stored PDF and the audit records created from {pendingDelete?.filename}. The action is the local stand-in for a privacy deletion.
            </DialogContent>
            <DialogActions>
              <Button appearance="secondary" onClick={() => setPendingDelete(null)}>
                Cancel
              </Button>
              <Button appearance="primary" onClick={() => pendingDelete && void remove(pendingDelete)}>
                Delete job
              </Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </div>
  );
}
