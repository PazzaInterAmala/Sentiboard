"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeftIcon, ArrowRightIcon } from "@/components/icons";
import { ErrorState, NotAvailableNotice, SENTIMENT_STYLE, SentimentChip } from "@/components/ui";
import { api, isNotAvailable } from "@/lib/api";
import { formatShortDate, percent } from "@/lib/format";
import { SENTIMENTS, type Paginated, type PostWithPrediction, type Sentiment } from "@/lib/types";

const PAGE_SIZE = 20;

/** Paginated posts with their prediction, filterable by label (plan §8.2). */
export default function PostsTable({ queryId, showSource }: { queryId: number; showSource: boolean }) {
  const [label, setLabel] = useState<Sentiment | undefined>();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<PostWithPrediction> | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await api.getPosts(queryId, page, PAGE_SIZE, label));
    } catch (err) {
      setError(err);
    }
  }, [queryId, page, label]);

  useEffect(() => { load(); }, [load]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const filters: Array<Sentiment | undefined> = [undefined, ...SENTIMENTS];

  if (error && isNotAvailable(error)) return <NotAvailableNotice feature="The posts list" />;

  return (
    <div>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter posts by sentiment">
        {filters.map((value) => (
          <button
            key={value ?? "all"}
            type="button"
            aria-pressed={label === value}
            onClick={() => { setLabel(value); setPage(1); }}
            className={`rounded border px-3 py-1.5 text-sm transition-colors ${label === value ? "border-ink bg-ink text-ivory" : "border-line bg-white text-charcoal hover:bg-ivory"}`}
          >
            {value ? SENTIMENT_STYLE[value].label : "All posts"}
          </button>
        ))}
      </div>

      {error !== null && <div className="mt-4"><ErrorState message={error instanceof Error ? error.message : "Posts could not be loaded."} onRetry={load} /></div>}

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-line text-label-md font-semibold uppercase text-muted">
            <tr>
              <th scope="col" className="py-3 pr-4 font-semibold">Post</th>
              {showSource && <th scope="col" className="px-4 py-3 font-semibold">Source</th>}
              <th scope="col" className="px-4 py-3 font-semibold">Date</th>
              <th scope="col" className="px-4 py-3 font-semibold">Sentiment</th>
              <th scope="col" className="py-3 pl-4 text-right font-semibold">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {!data && !error && [0, 1, 2].map((i) => <tr key={i}><td colSpan={5} className="py-3"><div className="h-10 animate-pulse rounded bg-ivory" /></td></tr>)}
            {data?.items.map((post) => (
              <tr key={post.post_id} className="border-b border-line align-top transition-colors hover:bg-sage/40">
                <td className="max-w-[560px] py-4 pr-4 text-charcoal">
                  <p className="line-clamp-3">{post.text}</p>
                  {post.url && <a href={post.url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-label-md font-normal text-accent-deep hover:underline">Open on Reddit ↗</a>}
                </td>
                {showSource && <td className="whitespace-nowrap px-4 py-4 text-muted">{post.subreddit ? `r/${post.subreddit}` : "—"}</td>}
                <td className="whitespace-nowrap px-4 py-4 text-muted">{post.post_date ? formatShortDate(post.post_date) : "—"}</td>
                <td className="px-4 py-4"><SentimentChip label={post.prediction.label} /></td>
                <td className="py-4 pl-4 text-right tabular-nums text-ink">{percent(post.prediction.confidence)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.items.length === 0 && <p className="py-8 text-center text-sm text-muted">No posts with this sentiment.</p>}
      </div>

      {data && totalPages > 1 && (
        <nav aria-label="Posts pages" className="mt-4 flex items-center justify-between text-sm">
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="btn-ghost min-h-9 px-3 py-1.5"><ArrowLeftIcon className="size-4" /> Previous</button>
          <span className="text-muted">Page {page} of {totalPages} · {data.total.toLocaleString()} posts</span>
          <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} className="btn-ghost min-h-9 px-3 py-1.5">Next <ArrowRightIcon className="size-4" /></button>
        </nav>
      )}
    </div>
  );
}
