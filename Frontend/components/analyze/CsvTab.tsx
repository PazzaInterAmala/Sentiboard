"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState, type DragEvent, type FormEvent } from "react";
import {
  AboutIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  AlertIcon,
  CloseIcon,
  FileIcon,
  InfoIcon,
  LightbulbIcon,
  SwapIcon,
  UploadIcon,
} from "@/components/icons";
import { ErrorState, NotAvailableNotice, Spinner } from "@/components/ui";
import { api, isNotAvailable } from "@/lib/api";
import {
  CSV_MAX_ROWS,
  dateColumnValidity,
  guessColumns,
  inspectCsv,
  summariseTextColumn,
  validateCsvFile,
  type CsvInspection,
} from "@/lib/csv";
import { percent } from "@/lib/format";

const SAMPLE_CSV = `text,created_at,rating
"The onboarding was crystal clear, though the reporting screen took a while to find.",2026-10-02,4
"Customer support answered our integration questions within an hour. Impressive.",2026-10-05,5
"Export formats are too limited for our workflow.",2026-10-09,2
`;

const DELIMITER_LABEL: Record<CsvInspection["delimiter"], string> = { ",": "Comma", ";": "Semicolon", "\t": "Tab" };

function formatSize(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function CsvTab() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [inspection, setInspection] = useState<CsvInspection | null>(null);
  const [textColumn, setTextColumn] = useState("");
  const [dateColumn, setDateColumn] = useState("");
  const [fileError, setFileError] = useState("");
  const [reading, setReading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<unknown>(null);

  const choose = async (next: File | undefined) => {
    if (!next) return;
    setSubmitError(null);
    const problem = validateCsvFile(next);
    if (problem) { setFileError(problem); return; }
    setReading(true);
    setFileError("");
    try {
      const result = await inspectCsv(next);
      if (!result.headers.length) throw new Error("We could not find a header row in this file.");
      if (!result.rows.length) throw new Error("This file has a header but no rows.");
      const guess = guessColumns(result);
      setFile(next);
      setInspection(result);
      setTextColumn(guess.text);
      setDateColumn(guess.date);
    } catch (err) {
      setFileError(err instanceof Error ? err.message : "We could not read this file.");
    } finally {
      setReading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const reset = () => { setFile(null); setInspection(null); setTextColumn(""); setDateColumn(""); setSubmitError(null); };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    choose(event.dataTransfer.files?.[0]);
  };

  const summary = useMemo(() => (inspection && textColumn ? summariseTextColumn(inspection, textColumn) : null), [inspection, textColumn]);
  const dateValidity = useMemo(() => (inspection && dateColumn ? dateColumnValidity(inspection, dateColumn) : null), [inspection, dateColumn]);
  const tooManyRows = (inspection?.rows.length ?? 0) > CSV_MAX_ROWS;
  const canSubmit = Boolean(file && textColumn && summary && summary.filled > 0 && !tooManyRows && !submitting);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || !canSubmit) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const job = await api.startCsvJob(file, textColumn, dateColumn || undefined);
      router.push(`/queries/${job.query_id}`);
    } catch (err) {
      setSubmitError(err);
      setSubmitting(false);
    }
  };

  const sampleHref = `data:text/csv;charset=utf-8,${encodeURIComponent(SAMPLE_CSV)}`;
  const previewColumns = inspection ? [textColumn, ...inspection.headers.filter((h) => h !== textColumn && h !== dateColumn).slice(0, 1)].filter(Boolean) : [];

  return (
    <div className="grid gap-6 lg:grid-cols-12 lg:items-start lg:gap-8">
      <form onSubmit={submit} className="card p-5 sm:p-10 lg:col-span-8">
        {file && inspection && (
          <div className="flex flex-col gap-4 rounded-md bg-sand/80 p-4 sm:flex-row sm:items-center">
            <span className="grid size-12 shrink-0 place-items-center rounded-md bg-line/60 text-ink"><FileIcon className="size-6" /></span>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 text-[15px] text-ink">
                <span className="truncate">{file.name}</span>
                <span className="shrink-0 rounded-sm bg-line/70 px-1.5 py-0.5 text-label-sm text-charcoal">{formatSize(file.size)}</span>
              </p>
              <p className="mt-1 text-sm text-charcoal">{inspection.rows.length.toLocaleString()} rows detected · {DELIMITER_LABEL[inspection.delimiter]} delimited</p>
            </div>
            <div className="flex gap-1">
              <button type="button" onClick={() => inputRef.current?.click()} className="btn-quiet text-sm font-medium"><SwapIcon className="size-4" /> Replace</button>
              <button type="button" onClick={reset} className="btn-quiet text-sm font-medium text-negative hover:text-negative"><CloseIcon className="size-4" /> Remove</button>
            </div>
          </div>
        )}

        {!file && (
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`flex flex-col items-center rounded-md border border-dashed px-6 py-14 text-center transition-colors ${dragging ? "border-accent bg-accent/[0.04]" : "border-line-strong bg-ivory"}`}
          >
            <span className="grid size-14 place-items-center rounded-md bg-sand text-ink">{reading ? <Spinner className="size-5" /> : <UploadIcon className="size-6" />}</span>
            <p className="mt-5 text-[17px] text-ink">
              Drag and drop your CSV file here, or{" "}
              <button type="button" onClick={() => inputRef.current?.click()} className="font-medium text-accent-deep underline underline-offset-4">browse files</button>
            </p>
            <p className="mt-2 max-w-md text-sm leading-6 text-charcoal">Supports .csv up to 5 MB and {CSV_MAX_ROWS.toLocaleString()} rows of reviews, comments or survey responses.</p>
          </div>
        )}
        <input ref={inputRef} type="file" accept=".csv,text/csv" className="sr-only" tabIndex={-1} aria-label="Choose CSV file" onChange={(e) => choose(e.target.files?.[0])} />
        {fileError && <div className="mt-4"><ErrorState title="This file can't be used" message={fileError} /></div>}

        {inspection && (
          <>
            <div className="mt-10 flex items-start justify-between gap-4">
              <div>
                <h2 className="font-serif text-headline-md text-ink">Column mapping</h2>
                <p className="mt-1 text-sm leading-6 text-charcoal">Choose the column to analyze and, optionally, a date column for the trend line.</p>
              </div>
              <span className="shrink-0 rounded-sm bg-sand px-2.5 py-1.5 text-label-md font-normal text-charcoal">{inspection.headers.length} columns</span>
            </div>

            <div className="mt-6 grid gap-6 md:grid-cols-2">
              <div>
                <div className="flex items-baseline justify-between">
                  <label htmlFor="csv-text-column" className="text-[15px] text-ink">Text column to analyze</label>
                  <span className="text-label-md font-semibold uppercase text-accent-deep">Required</span>
                </div>
                <select id="csv-text-column" value={textColumn} onChange={(e) => setTextColumn(e.target.value)} className="field mt-2 h-[52px] border-transparent bg-sand text-base focus:bg-white">
                  {inspection.headers.map((h) => <option key={h} value={h}>{h}</option>)}
                </select>
                <p className="mt-2 text-sm leading-6 text-charcoal">The verbatim sentences evaluated for sentiment.</p>
              </div>
              <div>
                <div className="flex items-baseline justify-between">
                  <label htmlFor="csv-date-column" className="text-[15px] text-ink">Date column</label>
                  <span className="text-label-md font-normal text-muted">Optional</span>
                </div>
                <select id="csv-date-column" value={dateColumn} onChange={(e) => setDateColumn(e.target.value)} className="field mt-2 h-[52px] border-transparent bg-sand text-base focus:bg-white">
                  <option value="">No date column</option>
                  {inspection.headers.filter((h) => h !== textColumn).map((h) => <option key={h} value={h}>{h}</option>)}
                </select>
                <p className="mt-2 text-sm leading-6 text-charcoal">Enables the sentiment-over-time chart.</p>
              </div>
            </div>

            <div className="mt-10">
              <div className="flex items-baseline justify-between">
                <h3 className="text-[15px] text-ink">Sample rows (first {Math.min(3, inspection.rows.length)} of {inspection.rows.length.toLocaleString()})</h3>
                <span className="text-label-md font-normal text-muted">Source preview</span>
              </div>
              <div className="mt-3 overflow-x-auto rounded-md border border-line">
                <table className="w-full min-w-[480px] text-left text-sm">
                  <thead className="bg-sand text-ink">
                    <tr>
                      <th scope="col" className="w-12 px-4 py-3 font-semibold">#</th>
                      {previewColumns.map((col) => <th key={col} scope="col" className="px-4 py-3 font-semibold">{col}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {inspection.rows.slice(0, 3).map((row, i) => (
                      <tr key={i} className="border-t border-line bg-ivory">
                        <td className="px-4 py-4 font-mono text-label-md text-muted">{String(i + 1).padStart(2, "0")}</td>
                        {previewColumns.map((col, c) => {
                          const value = row[inspection.headers.indexOf(col)] ?? "";
                          return <td key={col} className={`px-4 py-4 text-charcoal ${c === 0 ? "max-w-[420px] truncate" : "whitespace-nowrap"}`} title={value}>{c === 0 && value ? `“${value}”` : value || "—"}</td>;
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {submitError !== null && (
          <div className="mt-6">
            {isNotAvailable(submitError)
              ? <NotAvailableNotice feature="CSV upload" />
              : <ErrorState title="We could not start this upload" message={submitError instanceof Error ? submitError.message : "Please try again."} />}
          </div>
        )}

        <div className="mt-10 flex flex-col-reverse gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2 text-sm text-charcoal"><InfoIcon className="size-4 text-muted" /> The file is read once; only the rows and results are stored.</p>
          <button type="submit" disabled={!canSubmit} className="btn-primary min-h-[52px] px-7 text-base">
            {submitting && <Spinner />}
            {submitting ? "Uploading…" : "Analyze file"}
            {!submitting && <ArrowRightIcon className="size-5" />}
          </button>
        </div>

        <p className="mt-10 flex items-start gap-2 border-t border-line pt-6 text-sm text-charcoal">
          <InfoIcon className="mt-0.5 size-4 shrink-0 text-muted" />
          <span>Need a starting point? <a href={sampleHref} download="sentiboard_sample.csv" className="font-medium text-accent-deep hover:underline">Download a sample feedback CSV</a>.</span>
        </p>
      </form>

      <div className="space-y-6 lg:col-span-4">
        <aside className="card p-6 sm:p-7">
          <p className="eyebrow">File check</p>
          <h2 className="mt-4 font-serif text-headline-md text-ink">Pre-flight assessment</h2>
          {!inspection || !summary ? (
            <p className="mt-3 text-sm leading-6 text-charcoal">Choose a file and we will check it here before anything is uploaded.</p>
          ) : (
            <>
              <p className="mt-3 text-[15px] leading-6 text-charcoal">
                A scan of <em className="font-serif text-ink">{file?.name}</em> found {summary.filled.toLocaleString()} texts to analyze in <strong className="font-medium text-ink">{textColumn}</strong>.
              </p>
              <div className="mt-5 rounded-md bg-sand/80 p-4">
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="text-charcoal">Mean length</span>
                  <span className="font-semibold text-ink">{Math.round(summary.meanWords)} words / row</span>
                </div>
                <div className="mt-3 flex h-1.5 overflow-hidden rounded-sm bg-line/70" aria-hidden="true">
                  <span className="bg-accent" style={{ width: percent(summary.share.elaborated) }} />
                  <span className="bg-[#becaba]" style={{ width: percent(summary.share.brief) }} />
                </div>
                <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-label-md font-normal text-charcoal">
                  <li className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-accent" />Elaborated {percent(summary.share.elaborated)}</li>
                  <li className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-[#becaba]" />Brief {percent(summary.share.brief)}</li>
                  <li className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-line" />Minimal {percent(summary.share.minimal)}</li>
                </ul>
              </div>
              <ul className="mt-5 space-y-3 text-sm leading-5 text-charcoal">
                <Check ok={summary.empty === 0}>{summary.empty === 0 ? "No empty values in the text column" : `${summary.empty.toLocaleString()} empty rows will be skipped`}</Check>
                <Check ok={!tooManyRows}>{tooManyRows ? `${inspection.rows.length.toLocaleString()} rows: over the ${CSV_MAX_ROWS.toLocaleString()} row limit` : `Within the ${CSV_MAX_ROWS.toLocaleString()} row limit`}</Check>
                {dateColumn && dateValidity !== null && (
                  <Check ok={dateValidity > 0.9}>{dateValidity > 0.9 ? "Dates in the date column look valid" : `Only ${percent(dateValidity)} of dates could be read`}</Check>
                )}
                <Check ok={summary.filled >= 50}>{summary.filled >= 50 ? "Enough texts for a meaningful split" : "Fewer than 50 texts: treat the split with care"}</Check>
              </ul>
            </>
          )}
        </aside>

        <aside className="rounded-md border border-line bg-sand/70 p-6 sm:p-7">
          <span className="grid size-9 place-items-center rounded-md bg-line/60 text-ink"><AboutIcon className="size-5" /></span>
          <h2 className="mt-4 font-serif text-headline-md text-ink">The qualitative standard</h2>
          <p className="mt-3 font-serif text-quote italic text-ink">“We treat feedback not as transactional rows, but as lived experience told by customers.”</p>
          <p className="mt-4 text-sm leading-6 text-charcoal">Once analyzed, every row keeps its text, so you can read the voices behind each number and export them with their sentiment.</p>
          <p className="mt-5 flex gap-3 rounded-md bg-ivory/70 p-4 text-sm leading-6 text-charcoal">
            <LightbulbIcon className="size-5 shrink-0 text-accent-deep" />
            Results are most reliable when a file holds at least 50 written responses.
          </p>
        </aside>
      </div>
    </div>
  );
}

function Check({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      {ok ? <CheckCircleIcon className="size-5 shrink-0 text-positive" /> : <AlertIcon className="size-5 shrink-0 text-negative" />}
      <span>{children}</span>
    </li>
  );
}
