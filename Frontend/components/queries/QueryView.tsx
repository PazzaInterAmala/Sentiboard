"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ResultCard from "@/components/analyze/ResultCard";
import { ArrowLeftIcon, DownloadIcon, RefreshIcon } from "@/components/icons";
import QueryDashboard from "@/components/queries/QueryDashboard";
import { EmptyState, ErrorState, StatusBadge } from "@/components/ui";
import { api, isApiError } from "@/lib/api";
import { QUERY_TYPE_LABEL, formatDate, queryTitle } from "@/lib/format";
import type { PostWithPrediction, Query } from "@/lib/types";

const POLL_MS = 2000; // plan §8.3

const RETRY_TAB: Record<Query["type"], string> = { text: "/analyze", keyword: "/analyze?tab=reddit", csv: "/analyze?tab=csv" };

export default function QueryView({ id }: { id: number }) {
  const [query, setQuery] = useState<Query | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      const next = await api.getQuery(id);
      setQuery(next);
      setError(null);
      return next;
    } catch (err) {
      setError(err);
      return null;
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // Poll every 2 s while the background job is running.
  const running = query?.status === "pending" || query?.status === "processing";
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(load, POLL_MS);
    return () => window.clearInterval(timer);
  }, [running, load]);

  if (error && !query) {
    const notFound = isApiError(error, 404);
    return (
      <div className="mx-auto max-w-2xl py-10">
        {notFound
          ? <EmptyState title="Analysis not found" action={<Link href="/history" className="btn-primary">Back to history</Link>}>It may have been removed, or it belongs to another account.</EmptyState>
          : <ErrorState title="This analysis could not be loaded" message={error instanceof Error ? error.message : "Please try again."} onRetry={load} />}
      </div>
    );
  }

  if (!query) {
    return <div className="space-y-6" aria-busy="true"><div className="h-24 animate-pulse rounded-md bg-ivory" /><div className="h-64 animate-pulse rounded-md bg-ivory" /></div>;
  }

  const title = query.type === "text" ? "Text analysis" : queryTitle(query);
  const sourceLine = query.type === "keyword"
    ? `Reddit search${query.params?.time_range ? ` · ${String(query.params.time_range)}` : ""}${query.params?.limit ? ` · up to ${String(query.params.limit)} posts` : ""}`
    : `${QUERY_TYPE_LABEL[query.type]} analysis`;

  return (
    <div>
      <Link href="/history" className="inline-flex items-center gap-1.5 text-sm text-charcoal hover:text-ink"><ArrowLeftIcon className="size-4" /> History</Link>
      <header className="mt-5 flex flex-col gap-5 border-b border-line pb-8 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <p className="eyebrow">{sourceLine}</p>
          <h1 className="mt-3 break-words font-serif text-display-md text-ink md:text-display-lg">{title}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-[15px] text-muted">
            <span>{formatDate(query.created_at)}</span>
            <StatusBadge status={query.status} />
          </div>
        </div>
        {query.status === "done" && query.type !== "text" && (query.post_count ?? 0) > 0 && (
          <a href={api.exportUrl(query.query_id)} download={`sentiboard_${query.query_id}.csv`} className="btn-ghost self-start md:self-auto">
            <DownloadIcon className="size-4" /> Export CSV
          </a>
        )}
      </header>

      <div className="mt-10">
        {running && <Processing query={query} />}

        {query.status === "failed" && (
          <ErrorState
            title="This analysis did not finish"
            message={query.error_message || "Something went wrong while processing."}
            action={<Link href={RETRY_TAB[query.type]} className="btn-primary min-h-9 px-3 py-1.5">Try again</Link>}
          />
        )}

        {query.status === "done" && query.type === "text" && <TextResult query={query} />}

        {query.status === "done" && query.type !== "text" && (query.post_count ?? 0) === 0 && (
          <EmptyState title="No posts found" action={<Link href={RETRY_TAB[query.type]} className="btn-primary">Try another search</Link>}>
            {query.type === "keyword" ? "Reddit returned no posts for this keyword and time window. Try a broader keyword or a longer window." : "The file had no usable rows in the chosen text column."}
          </EmptyState>
        )}

        {query.status === "done" && query.type !== "text" && (query.post_count ?? 0) > 0 && <QueryDashboard query={query} />}
      </div>
    </div>
  );
}

function Processing({ query }: { query: Query }) {
  return (
    <div className="card flex flex-col items-center px-6 py-16 text-center" role="status" aria-live="polite">
      <RefreshIcon className="size-8 animate-spin text-accent [animation-duration:2.5s]" />
      <h2 className="mt-6 font-serif text-headline-md text-ink">{query.status === "pending" ? "Queued for reading" : "Reading every post"}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-charcoal">
        {query.type === "keyword" ? "Collecting Reddit posts and running each one through the sentiment model." : "Running each row of your file through the sentiment model."}
        {" "}This page updates by itself. You can leave and come back from History.
      </p>
    </div>
  );
}

/** A single text: show the stored text and the model verdict (from the posts endpoint). */
function TextResult({ query }: { query: Query }) {
  const [post, setPost] = useState<PostWithPrediction | null | undefined>(undefined);

  useEffect(() => {
    api.getPosts(query.query_id, 1, 1).then((page) => setPost(page.items[0] ?? null)).catch(() => setPost(null));
  }, [query.query_id]);

  const text = post?.text ?? query.keyword ?? "";
  return (
    <div className="mx-auto max-w-[960px] space-y-6">
      <blockquote className="card-ivory p-6 font-serif text-quote text-ink sm:p-8">“{text}”</blockquote>
      {post === undefined && <div className="h-48 animate-pulse rounded-md bg-ivory" />}
      {post && <ResultCard result={post.prediction} />}
      {post === null && (
        <div className="card-ivory p-6">
          <p className="eyebrow">Result</p>
          <p className="mt-3 font-serif text-headline-md text-ink">{query.positive_share === 1 ? "Positive" : "Not positive"}</p>
          <p className="mt-1 text-sm text-muted">Full probabilities appear here once the posts endpoint is available on the API.</p>
        </div>
      )}
      <Link href="/analyze" className="btn-ghost">Analyze another text</Link>
    </div>
  );
}
