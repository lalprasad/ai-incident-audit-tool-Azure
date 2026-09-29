import { useEffect, useState } from "react";

import { ApiError, request } from "../services/api";
import type { AuditJob } from "../types/audit";

export function useJob(jobId: string | null) {
  const [job, setJob] = useState<AuditJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }
    let stop = false;
    let timer = 0;

    const tick = async () => {
      try {
        const next = await request<AuditJob>(`/api/audits/jobs/${jobId}`);
        if (stop) return;
        setJob(next);
        setError(null);
        if (next.status === "Completed" || next.status === "Failed") return;
        timer = window.setTimeout(() => void tick(), 400);
      } catch (caught) {
        if (stop) return;
        setError(caught instanceof ApiError ? caught.message : "Status check failed.");
      }
    };

    void tick();
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
  }, [jobId]);

  return { job, error };
}
