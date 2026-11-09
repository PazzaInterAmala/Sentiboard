"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeftIcon, ArrowRightIcon, HistoryIcon, PlusIcon, RefreshIcon, SearchIcon } from "@/components/icons";
import { EmptyState, ErrorState, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { QUERY_TYPE_LABEL, formatDate, queryTitle } from "@/lib/format";
import type { Paginated, Query } from "@/lib/types";

const PAGE_SIZE = 20;
const REFRESH_MS = 5000;

function actionFor(query: Query) {
  if (query.status === "done") return { label: "View results", className: "text-ink" };
  if (query.status === "failed") return { label: "View details", className: "text-ink" };
  return { label: "View progress", className: "text-accent-deep" };
}

export default function HistoryList() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<Query> | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const load = useCallback(async (silent = false) => {
    if (!silent) setError("");
    try {
      setData(await api.listQueries(page, PAGE_SIZE));
    } catch (err) {
      if (!silent) setError(err instanceof Error ? err.message : "Your history could not be loaded.");
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  // Keep running jobs fresh without a manual reload.
  const hasRunning = data?.items.some((q) => q.status === "pending" || q.status === "processing");
  useEffect(() => {
    if (!hasRunning) return;
    const timer = window.setInterval(() => load(true), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [hasRunning, load]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!data || !term) return data?.items ?? [];
    return data.items.filter((q) => `${queryTitle(q)} ${q.keyword ?? ""} ${q.file_name ?? ""} ${QUERY_TYPE_LABEL[q.type]}`.toLowerCase().includes(term));
  }, [data, search]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <header className="flex flex-col gap-5 border-b border-line pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-serif text-display-md text-ink md:text-display-lg">History</h1>
          <p className="mt-2 text-base text-charcoal">Past sentiment analyses and reviews.</p>
        </div>
        <Link href="/analyze" className="btn-primary self-start sm:self-auto"><PlusIcon className="size-5" /> New analysis</Link>
      </header>

      <div className="mt-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full max-w-xl">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted" />
          <label htmlFor="history-search" className="sr-only">Search past analyses</label>
          <input id="history-search" type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search past analyses…" className="field h-12 border-transparent bg-sand pl-12 text-[15px] focus:bg-white" />
        </div>
        {data && <p className="text-label-md font-normal text-muted">{data.total.toLocaleString()} {data.total === 1 ? "analysis" : "analyses"} recorded</p>}
      </div>

      <div className="mt-10">
        {error && <ErrorState title="Your history could not be loaded" message={error} onRetry={() => load()} />}

        {!data && !error && (
          <div className="card divide-y divide-line" aria-busy="true" aria-label="Loading history">
            {[0, 1, 2, 3].map((i) => <div key={i} className="h-[104px] animate-pulse bg-ivory" />)}
          </div>
        )}

        {data && data.total === 0 && (
          <EmptyState title="No analyses yet" action={<Link href="/analyze" className="btn-primary">Start your first analysis <ArrowRightIcon className="size-4" /></Link>}>
            Every text, Reddit search and CSV upload you analyze is saved here, so you can come back to it later.
          </EmptyState>
        )}

        {data && data.total > 0 && filtered.length === 0 && (
          <EmptyState title="No matches on this page">Try a different word, or clear the search.</EmptyState>
        )}

        {filtered.length > 0 && (
          <ul className="card divide-y divide-line overflow-hidden">
            {filtered.map((query) => {
              const action = actionFor(query);
              const running = query.status === "pending" || query.status === "processing";
              return (
                <li key={query.query_id}>
                  <Link href={`/queries/${query.query_id}`} className={`flex flex-col gap-4 px-5 py-6 transition-colors hover:bg-sage/40 sm:flex-row sm:items-center sm:px-8 ${running ? "bg-ivory" : ""}`}>
                    <div className="min-w-0 flex-1">
                      <p className="flex items-center gap-2 text-[19px] leading-7 text-ink">
                        <span className="truncate">{queryTitle(query)}</span>
                        {running && <RefreshIcon className="size-4 shrink-0 animate-spin text-accent [animation-duration:2.5s]" aria-label="Processing" />}
                      </p>
                      <p className="mt-1 flex flex-wrap items-center gap-x-2 text-[15px] text-muted">
                        <span>{formatDate(query.created_at)}</span>
                        <span aria-hidden="true">·</span>
                        <span>{QUERY_TYPE_LABEL[query.type]}</span>
                        {query.post_count !== null && query.type !== "text" && <><span aria-hidden="true">·</span><span>{query.post_count.toLocaleString()} posts</span></>}
                      </p>
                    </div>
                    <div className="flex items-center justify-between gap-3 sm:justify-end sm:gap-6">
                      <StatusBadge status={query.status} positiveShare={query.type === "text" ? null : query.positive_share} />
                      <span className={`inline-flex shrink-0 items-center justify-end gap-1.5 text-[15px] sm:min-w-[124px] ${action.className}`}>
                        {action.label} <ArrowRightIcon className="size-4" />
                      </span>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}

        {data && totalPages > 1 && (
          <nav aria-label="History pages" className="mt-6 flex items-center justify-between text-sm">
            <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="btn-ghost"><ArrowLeftIcon className="size-4" /> Newer</button>
            <span className="text-muted">Page {page} of {totalPages}</span>
            <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} className="btn-ghost">Older <ArrowRightIcon className="size-4" /></button>
          </nav>
        )}
      </div>

      <div className="mt-12 flex flex-col gap-3 rounded-md border border-line bg-sand/70 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-3 text-[15px] text-charcoal"><HistoryIcon className="size-5 shrink-0 text-muted" /> Analyses are saved automatically so you can revisit past findings and trends anytime.</p>
        <Link href="/analyze" className="shrink-0 text-[15px] font-medium text-ink hover:text-accent-deep">Start new run →</Link>
      </div>
    </div>
  );
}
