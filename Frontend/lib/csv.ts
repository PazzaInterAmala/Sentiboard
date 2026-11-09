// Client-side CSV inspection for the upload tab: headers, row count, preview rows
// and a quick quality summary, so the user can choose columns before uploading.
// Limits match the backend contract (docs/IMPLEMENTATION_PLAN.md §6.2).

export const CSV_MAX_BYTES = 5 * 1024 * 1024;
export const CSV_MAX_ROWS = 5000;

export type CsvInspection = {
  headers: string[];
  rows: string[][]; // data rows (header excluded)
  delimiter: "," | ";" | "\t";
};

/** RFC 4180 style parser: quoted fields, escaped quotes, CRLF/LF, embedded newlines. */
export function parseCsv(text: string, delimiter: CsvInspection["delimiter"]): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (inQuotes) {
      if (char === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 1; } else inQuotes = false;
      } else field += char;
      continue;
    }
    if (char === '"') inQuotes = true;
    else if (char === delimiter) { row.push(field); field = ""; }
    else if (char === "\n" || char === "\r") {
      if (char === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field); field = "";
      rows.push(row); row = [];
    } else field += char;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.some((cell) => cell.trim() !== ""));
}

function detectDelimiter(firstLine: string): CsvInspection["delimiter"] {
  const counts = { ",": 0, ";": 0, "\t": 0 } as Record<CsvInspection["delimiter"], number>;
  let inQuotes = false;
  for (const char of firstLine) {
    if (char === '"') inQuotes = !inQuotes;
    else if (!inQuotes && char in counts) counts[char as CsvInspection["delimiter"]] += 1;
  }
  return (Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0] as CsvInspection["delimiter"]) || ",";
}

async function decode(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(buffer).replace(/^﻿/, "");
  } catch {
    return new TextDecoder("latin1").decode(buffer); // same fallback as the backend
  }
}

export async function inspectCsv(file: File): Promise<CsvInspection> {
  const text = await decode(file);
  const firstLine = text.slice(0, text.search(/\r?\n/) === -1 ? undefined : text.search(/\r?\n/));
  const delimiter = detectDelimiter(firstLine);
  const [headerRow = [], ...rows] = parseCsv(text, delimiter);
  const headers = headerRow.map((h, i) => h.trim() || `column_${i + 1}`);
  return { headers, rows, delimiter };
}

export function validateCsvFile(file: File): string | null {
  if (!/\.csv$/i.test(file.name)) return "Please choose a .csv file.";
  if (file.size === 0) return "This file is empty.";
  if (file.size > CSV_MAX_BYTES) return `This file is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is 5 MB.`;
  return null;
}

const TEXT_HINTS = /^(text|review|comment|feedback|body|content|message|response|answer|tweet|post)/i;
const DATE_HINTS = /(date|time|created|posted|timestamp|_at$)/i;

function columnValues(inspection: CsvInspection, column: string): string[] {
  const index = inspection.headers.indexOf(column);
  return index < 0 ? [] : inspection.rows.map((row) => (row[index] ?? "").trim());
}

function averageWords(values: string[]): number {
  const filled = values.filter(Boolean);
  if (!filled.length) return 0;
  return filled.reduce((sum, v) => sum + v.split(/\s+/).length, 0) / filled.length;
}

/** Guess the text column (name hint, else longest average content) and a date column. */
export function guessColumns(inspection: CsvInspection): { text: string; date: string } {
  const { headers } = inspection;
  const byName = headers.find((h) => TEXT_HINTS.test(h) && !DATE_HINTS.test(h));
  const byLength = [...headers].sort((a, b) => averageWords(columnValues(inspection, b)) - averageWords(columnValues(inspection, a)))[0];
  const date = headers.find((h) => DATE_HINTS.test(h) && columnValues(inspection, h).slice(0, 20).some(looksLikeDate)) ?? "";
  return { text: byName ?? byLength ?? headers[0] ?? "", date };
}

function looksLikeDate(value: string): boolean {
  return Boolean(value) && !Number.isNaN(Date.parse(value));
}

export type ColumnSummary = {
  filled: number;
  empty: number;
  meanWords: number;
  share: { elaborated: number; brief: number; minimal: number }; // >25 words, 6-25, ≤5
};

export function summariseTextColumn(inspection: CsvInspection, column: string): ColumnSummary {
  const values = columnValues(inspection, column);
  const filled = values.filter(Boolean);
  const words = filled.map((v) => v.split(/\s+/).length);
  const total = filled.length || 1;
  return {
    filled: filled.length,
    empty: values.length - filled.length,
    meanWords: averageWords(values),
    share: {
      elaborated: words.filter((w) => w > 25).length / total,
      brief: words.filter((w) => w > 5 && w <= 25).length / total,
      minimal: words.filter((w) => w <= 5).length / total,
    },
  };
}

export function dateColumnValidity(inspection: CsvInspection, column: string): number {
  const values = columnValues(inspection, column).filter(Boolean);
  if (!values.length) return 0;
  return values.filter(looksLikeDate).length / values.length;
}
