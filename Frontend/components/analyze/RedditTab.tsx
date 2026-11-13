"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import RecentQueries from "@/components/analyze/RecentQueries";
import { ArrowRightIcon, CloseIcon, LayersIcon, SearchIcon } from "@/components/icons";
import { ErrorState, NotAvailableNotice, Spinner } from "@/components/ui";
import { api, isNotAvailable } from "@/lib/api";
import type { TimeRange } from "@/lib/types";

// Backend limits (plan §6.2): keyword 1–100 chars, limit 10–500, time_range enum.
const KEYWORD_MAX = 100;
const LIMIT_MIN = 10;
const LIMIT_MAX = 500;
const DEPTHS = [50, 100, 250] as const;
const TIME_RANGES: Array<{ value: TimeRange; label: string }> = [
  { value: "day", label: "Past 24 hours" },
  { value: "week", label: "Past week" },
  { value: "month", label: "Past month (recommended)" },
  { value: "year", label: "Past year" },
  { value: "all", label: "All time" },
];
const SUGGESTIONS = ["iPhone 17", "remote work", "electric cars", "Notion AI"];

export default function RedditTab() {
  const router = useRouter();
  const [keyword, setKeyword] = useState("");
  const [depth, setDepth] = useState<number | "custom">(100);
  const [customLimit, setCustomLimit] = useState("150");
  const [timeRange, setTimeRange] = useState<TimeRange>("month");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const limit = depth === "custom" ? Number(customLimit) : depth;
  const limitValid = Number.isInteger(limit) && limit >= LIMIT_MIN && limit <= LIMIT_MAX;
  const trimmed = keyword.trim();
  const canSubmit = trimmed.length > 0 && trimmed.length <= KEYWORD_MAX && limitValid && !submitting;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const job = await api.startKeywordJob({ keyword: trimmed, limit, time_range: timeRange });
      router.push(`/queries/${job.query_id}`);
    } catch (err) {
      setError(err);
      setSubmitting(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-12 lg:items-start lg:gap-8">
      <form onSubmit={submit} className="card p-5 sm:p-10 lg:col-span-8">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <label htmlFor="reddit-keyword" className="text-[17px] font-semibold text-ink">Topic or keyword</label>
          <span className="text-label-md font-normal text-muted">Searched across Reddit posts</span>
        </div>
        <div className="relative mt-3">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted" />
          <input
            id="reddit-keyword"
            value={keyword}
            maxLength={KEYWORD_MAX}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="e.g. Linear app migration"
            autoComplete="off"
            className="field h-14 border-transparent bg-sand/80 pl-12 pr-12 text-base focus:bg-white"
          />
          {keyword && (
            <button type="button" onClick={() => setKeyword("")} className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1.5 text-muted hover:text-ink" aria-label="Clear keyword">
              <CloseIcon className="size-4" />
            </button>
          )}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-label-md font-normal text-charcoal">
          <span>Suggested:</span>
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" onClick={() => setKeyword(s)} className="rounded-sm bg-sand px-2.5 py-1 hover:bg-sage/60">{s}</button>
          ))}
        </div>

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          <fieldset>
            <div className="flex items-baseline justify-between">
              <legend className="text-[15px] font-medium text-ink">Sampling depth</legend>
              <span className="text-label-md font-normal text-muted">Posts analyzed</span>
            </div>
            <div className="mt-3 grid grid-cols-4 rounded-md bg-sand p-1">
              {[...DEPTHS, "custom" as const].map((option) => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={depth === option}
                  onClick={() => setDepth(option)}
                  className={`rounded px-2 py-2.5 text-sm font-medium transition-colors ${depth === option ? "bg-white text-ink" : "text-charcoal hover:text-ink"}`}
                >
                  {option === "custom" ? "Custom" : option}
                </button>
              ))}
            </div>
            {depth === "custom" && (
              <div className="mt-3">
                <label htmlFor="reddit-limit" className="sr-only">Number of posts</label>
                <input
                  id="reddit-limit"
                  type="number"
                  inputMode="numeric"
                  min={LIMIT_MIN}
                  max={LIMIT_MAX}
                  value={customLimit}
                  onChange={(e) => setCustomLimit(e.target.value)}
                  aria-invalid={!limitValid}
                  className="field h-11"
                />
                <p className={`mt-1.5 text-label-md font-normal ${limitValid ? "text-muted" : "text-negative"}`}>Between {LIMIT_MIN} and {LIMIT_MAX} posts.</p>
              </div>
            )}
          </fieldset>
          <div>
            <div className="flex items-baseline justify-between">
              <label htmlFor="reddit-range" className="text-[15px] font-medium text-ink">Observation window</label>
              <span className="text-label-md font-normal text-muted">Post creation</span>
            </div>
            <select id="reddit-range" value={timeRange} onChange={(e) => setTimeRange(e.target.value as TimeRange)} className="field mt-3 h-[52px] border-transparent bg-sand text-base focus:bg-white">
              {TIME_RANGES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
        </div>

        <div className="mt-10 flex gap-4 rounded-md bg-sand/70 p-5 sm:p-6">
          <LayersIcon className="mt-0.5 size-6 shrink-0 text-accent-deep" />
          <div>
            <p className="text-[15px] leading-6 text-ink">SentiBoard collects matching Reddit posts and reads each one with the sentiment model.</p>
            <p className="mt-1 text-sm leading-6 text-muted">The analysis runs in the background. You will see a progress view, then a dashboard with the sentiment split, trend over time, recurring words and the posts themselves.</p>
          </div>
        </div>

        {error !== null && (
          <div className="mt-6">
            {isNotAvailable(error)
              ? <NotAvailableNotice feature="Reddit search" />
              : <ErrorState title="We could not start this search" message={error instanceof Error ? error.message : "Please try again."} />}
          </div>
        )}

        <div className="mt-10 flex flex-col-reverse gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-label-md font-normal text-muted">Read-only: SentiBoard never posts to Reddit.</p>
          <button type="submit" disabled={!canSubmit} className="btn-primary min-h-[52px] px-8 text-base sm:min-w-[240px]">
            {submitting ? <Spinner /> : null}
            {submitting ? "Starting…" : "Analyze posts"}
            {!submitting && <ArrowRightIcon className="size-5" />}
          </button>
        </div>
      </form>

      <div className="lg:col-span-4">
        <RecentQueries type="keyword" title="Recent Reddit searches" intro="Searches you ran before, ready to review again." />
      </div>
    </div>
  );
}
