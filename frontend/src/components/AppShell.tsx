import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { ApiError, request } from "../services/api";
import type { Health } from "../types/audit";

export function AppShell() {
  const [health, setHealth] = useState<Health | null>(null);
  const [offline, setOffline] = useState<string | null>(null);

  useEffect(() => {
    request<Health>("/api/health")
      .then((body) => {
        setHealth(body);
        setOffline(null);
      })
      .catch((error: unknown) => {
        setOffline(error instanceof ApiError ? error.message : "The audit API is not reachable.");
      });
  }, []);

  return (
    <>
      <header className="app-header">
        <div className="brand">
          <strong>INCIDENT AUDIT</strong>
          <span>ServiceNow ticket quality</span>
        </div>
        <nav className="nav" aria-label="Primary">
          <NavLink to="/" end>
            New audit
          </NavLink>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/history">History</NavLink>
        </nav>
        <div className="header-meta">
          <span className="pill">
            {health?.use_mock_azure === false
              ? health.azure_mode === "managed_identity"
                ? "Azure AI (MI)"
                : "Azure AI"
              : "Mock Azure"}
          </span>
          {health?.openai_deployment ? (
            <span className="pill">{health.openai_deployment}</span>
          ) : null}
          <span className="pill">Criteria {health?.criteria_version ?? "—"}</span>
        </div>
      </header>
      <main>
        {offline ? (
          <div className="panel" role="alert" style={{ marginBottom: 16 }}>
            {offline} Start the API on port 43124 and refresh this page.
          </div>
        ) : null}
        <Outlet />
      </main>
    </>
  );
}
