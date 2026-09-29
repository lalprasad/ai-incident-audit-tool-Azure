export function formatPercent(value: number): string {
  return `${Number(value.toFixed(2))}%`;
}

export function formatScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export function formatWhen(value: string | null | undefined): string {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function badgeColor(
  classification: string,
): "success" | "brand" | "warning" | "danger" | "informative" {
  if (classification === "Excellent") return "success";
  if (classification === "Good") return "brand";
  if (classification === "Fair") return "warning";
  if (classification === "Needs Improvement") return "danger";
  return "informative";
}

export function barColor(classification: string): string {
  if (classification === "Excellent") return "#0e7a3d";
  if (classification === "Good") return "#0f6cbd";
  if (classification === "Fair") return "#8a6116";
  if (classification === "Needs Improvement") return "#a4262c";
  return "#0f6cbd";
}
