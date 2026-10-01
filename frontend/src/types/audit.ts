export type JobStatus =
  | "Uploaded"
  | "Extracting"
  | "Tickets identified"
  | "Auditing"
  | "Completed"
  | "Failed";

export type Evidence = {
  text: string;
  source_section: string;
  ticket_field: string;
  relevance: string;
  evidence_status: "Supported" | "Insufficient evidence";
  timestamp: string | null;
  page: number | null;
};

export type Measure = {
  measure_id: string;
  measure_name: string;
  ai_score: number;
  auditor_score: number | null;
  final_score: number;
  auditor_comments: string | null;
  override_reason: string | null;
  overridden: boolean;
  confidence: number;
  confidence_label: string;
  evidence: Evidence[];
  strengths: string[];
  gaps: string[];
  recommendation: string;
  ai_score_is_system_extension: boolean;
  final_score_is_system_extension: boolean;
  guidance: string;
};

export type TimelineEvent = {
  timestamp: string | null;
  author: string | null;
  event_type: string;
  text: string;
  audience: "customer" | "internal" | "unknown";
};

export type TicketSnapshot = {
  ticket_id: string | null;
  short_description: string | null;
  description: string | null;
  priority: string | null;
  severity: string | null;
  assignment_group: string | null;
  assigned_to: string | null;
  caller: string | null;
  business_service: string | null;
  configuration_item: string | null;
  opened_at: string | null;
  updated_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  state: string | null;
  work_notes: string | null;
  additional_comments: string | null;
  resolution_notes: string | null;
  resolution_code: string | null;
  cause: string | null;
  close_notes: string | null;
  source_pages: number[];
  timeline: TimelineEvent[];
};

export type AuditRecord = {
  id: string;
  ticket_id: string;
  audit_version: number;
  audited_at: string;
  job_id: string;
  overall_score: number;
  maximum_score: number;
  percentage: number;
  classification: string;
  totals_computed_by: string;
  ai_model: string;
  criteria_version: string;
  prompt_version: string;
  model_version: string;
  measures: Measure[];
  human_review_required: boolean;
  review_reasons: string[];
  auditor_override: boolean;
  auditor_review: { decision: string; comments: string | null; reviewed_at: string } | null;
  overall_strengths: string[];
  overall_gaps: string[];
  recommended_actions: string[];
  ticket: TicketSnapshot;
};

export type AuditSummary = {
  id: string;
  ticket_id: string;
  audit_version: number;
  audited_at: string;
  job_id: string;
  overall_score: number;
  maximum_score: number;
  percentage: number;
  classification: string;
  human_review_required: boolean;
  auditor_override: boolean;
  short_description: string | null;
  priority: string | null;
  state: string | null;
  opened_at: string | null;
};

export type AuditJob = {
  id: string;
  filename: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  error: string | null;
  ticket_ids: string[];
  audit_ids: string[];
  warnings: string[];
  stage_timings_ms: Record<string, number>;
  stages: string[];
};

export type NamedCount = { label: string; count: number };

export type DashboardSummary = {
  total_tickets: number;
  average_score: number;
  average_percentage: number;
  maximum_score: number;
  classifications: NamedCount[];
  human_review_count: number;
  measure_averages: { measure_id: string; measure_name: string; average: number }[];
  score_distribution: { score: number; count: number }[];
  quality_distribution: NamedCount[];
  common_gaps: { text: string; count: number }[];
  score_trend: { date: string; average_percentage: number; tickets: number }[];
  executive_summary: string;
  criteria_version: string;
  totals_computed_by: string;
  empty: boolean;
  review_reason_counts: NamedCount[];
};

export type Health = {
  status: string;
  use_mock_azure: boolean;
  azure_mode?: string;
  criteria_version: string;
  service: string;
  openai_deployment?: string | null;
};
