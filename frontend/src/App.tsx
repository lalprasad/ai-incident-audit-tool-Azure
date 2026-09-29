import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { TicketPage } from "./pages/TicketPage";
import { UploadPage } from "./pages/UploadPage";

export function App() {
  return (
    <FluentProvider theme={webLightTheme}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<UploadPage />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="tickets/:ticketId" element={<TicketPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </FluentProvider>
  );
}
