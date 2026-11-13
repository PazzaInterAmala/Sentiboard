import type { Query } from "@/lib/types";

export function percent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-US", { month: "long", day: "2-digit", year: "numeric" });
}

export function formatShortDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const day = 24 * 60 * 60 * 1000;
  if (diff < 60 * 60 * 1000) return "just now";
  if (diff < day) return `${Math.round(diff / (60 * 60 * 1000))} h ago`;
  if (diff < 7 * day) return `${Math.round(diff / day)} days ago`;
  return formatShortDate(iso);
}

/** Human title for a query: keyword, file name, or the first words of a text. */
export function queryTitle(query: Query): string {
  if (query.type === "csv") return query.file_name || `CSV upload #${query.query_id}`;
  if (query.type === "keyword") return query.keyword || `Reddit search #${query.query_id}`;
  const text = (query.keyword ?? "").trim();
  if (!text) return `Text analysis #${query.query_id}`;
  return text.length > 72 ? `${text.slice(0, 72).trimEnd()}…` : text;
}

export const QUERY_TYPE_LABEL: Record<Query["type"], string> = {
  text: "Text",
  keyword: "Reddit",
  csv: "CSV",
};

export function modelLabel(name: string): string {
  const known: Record<string, string> = { distilbert: "DistilBERT", baseline: "Baseline (TF-IDF)" };
  return known[name.toLowerCase()] ?? name;
}
