"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import ExamplePosts from "@/components/queries/ExamplePosts";
import PostsTable from "@/components/queries/PostsTable";
import { DistributionBar, ErrorState, NotAvailableNotice, SENTIMENT_STYLE } from "@/components/ui";
import { api, isNotAvailable } from "@/lib/api";
import { percent } from "@/lib/format";
import { SENTIMENTS, type Dashboard, type Query, type Sentiment } from "@/lib/types";

const SentimentOverTime = dynamic(() => import("@/components/queries/SentimentOverTime"), {
  ssr: false,
  loading: () => <div className="h-[280px] animate-pulse rounded-md bg-ivory sm:h-[320px]" />,
});

/** Dashboard for a finished keyword/CSV query (plan §8 / design 07_dashboard). */
export default function QueryDashboard({ query }: { query: Query }) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    api.getDashboard(query.query_id)
      .then((d) => !cancelled && setDashboard(d))
      .catch((err) => !cancelled && setError(err));
    return () => { cancelled = true; };
  }, [query.query_id, attempt]);

  const total = query.post_count ?? 0;

  return (
    <div className="space-y-12">
      {error !== null && (isNotAvailable(error)
        ? <><NotAvailableNotice feature="The dashboard" /><FallbackSummary query={query} /></>
        : <ErrorState title="The dashboard could not be loaded" message={error instanceof Error ? error.message : "Please try again."} onRetry={() => setAttempt((a) => a + 1)} />)}

      {!dashboard && error === null && <div className="grid gap-4 sm:grid-cols-3">{[0, 1, 2].map((i) => <div key={i} className="h-32 animate-pulse rounded-md bg-ivory" />)}</div>}

      {dashboard && (
        <>
          <SummaryCards dashboard={dashboard} total={total} />

          <section aria-labelledby="split-heading" className="card p-6 sm:p-8">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 id="split-heading" className="font-serif text-headline-md text-ink">Sentiment split</h2>
              <p className="text-label-md font-normal text-muted">{total.toLocaleString()} posts</p>
            </div>
            <DistributionBar split={dashboard.split} className="mt-6 h-4" />
            <dl className="mt-5 grid gap-4 sm:grid-cols-3">
              {SENTIMENTS.map((s) => (
                <div key={s} className="flex items-baseline gap-3">
                  <span aria-hidden="true" className={`size-2.5 rounded-sm ${SENTIMENT_STYLE[s].bar}`} />
                  <dt className="text-sm text-charcoal">{SENTIMENT_STYLE[s].label}</dt>
                  <dd className="ml-auto text-sm tabular-nums text-ink sm:ml-0"><span className="font-semibold">{percent(dashboard.split[s])}</span> <span className="text-muted">({dashboard.counts[s].toLocaleString()})</span></dd>
                </div>
              ))}
            </dl>
          </section>

          {/* All posts on one day (typical for CSV without dates) → no line chart (plan §6.4). */}
          {dashboard.per_day.length > 1 && (
            <section aria-labelledby="trend-heading" className="card p-6 sm:p-8">
              <h2 id="trend-heading" className="font-serif text-headline-md text-ink">Sentiment over time</h2>
              <p className="mt-1 text-sm text-muted">Posts per day for each tone.</p>
              <div className="mt-6"><SentimentOverTime perDay={dashboard.per_day} /></div>
            </section>
          )}

          <TopWords topWords={dashboard.top_words} />
        </>
      )}

      {total > 0 && <ExamplePosts queryId={query.query_id} />}

      <section aria-labelledby="posts-heading">
        <h2 id="posts-heading" className="font-serif text-headline-md text-ink">All posts</h2>
        <div className="mt-5 card p-5 sm:p-6"><PostsTable queryId={query.query_id} showSource={query.type === "keyword"} /></div>
      </section>
    </div>
  );
}

function SummaryCards({ dashboard, total }: { dashboard: Dashboard; total: number }) {
  const dominant = SENTIMENTS.reduce<Sentiment>((best, s) => (dashboard.split[s] > dashboard.split[best] ? s : best), "positive");
  const cards = [
    { label: "Posts analyzed", value: total.toLocaleString(), note: "Texts read by the model" },
    { label: "Positive sentiment", value: percent(dashboard.split.positive), note: `${percent(dashboard.split.negative)} negative · ${percent(dashboard.split.neutral)} neutral` },
    { label: "Prevailing tone", value: SENTIMENT_STYLE[dominant].label, note: `${percent(dashboard.split[dominant])} of all posts`, className: SENTIMENT_STYLE[dominant].text },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {cards.map((card) => (
        <section key={card.label} className="card-ivory p-6">
          <p className="eyebrow">{card.label}</p>
          <p className={`mt-4 font-serif text-[40px] leading-[48px] ${card.className ?? "text-ink"}`}>{card.value}</p>
          <p className="mt-1 text-sm text-muted">{card.note}</p>
        </section>
      ))}
    </div>
  );
}

function TopWords({ topWords }: { topWords: Dashboard["top_words"] }) {
  return (
    <section aria-labelledby="words-heading">
      <h2 id="words-heading" className="font-serif text-headline-md text-ink">Recurring words</h2>
      <p className="mt-1 text-sm text-muted">The ten most frequent words in each tone.</p>
      <div className="mt-6 grid gap-5 md:grid-cols-3">
        {SENTIMENTS.map((s) => {
          const words = topWords[s] ?? [];
          const max = Math.max(1, ...words.map((w) => w.count));
          return (
            <div key={s} className="card p-6">
              <p className={`text-label-md font-semibold uppercase ${SENTIMENT_STYLE[s].text}`}>{SENTIMENT_STYLE[s].label}</p>
              {words.length === 0 ? <p className="mt-4 text-sm text-muted">Not enough text.</p> : (
                <ol className="mt-4 space-y-2.5">
                  {words.map((w) => (
                    <li key={w.word} className="grid grid-cols-[minmax(0,7rem)_1fr_2.5rem] items-center gap-3 text-sm">
                      <span className="truncate text-ink">{w.word}</span>
                      <span className="h-1.5 overflow-hidden rounded-sm bg-sand"><span className={`block h-full ${SENTIMENT_STYLE[s].bar} opacity-80`} style={{ width: `${(w.count / max) * 100}%` }} /></span>
                      <span className="text-right tabular-nums text-muted">{w.count}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

/** What we can show from `GET /queries/{id}` alone. */
function FallbackSummary({ query }: { query: Query }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <section className="card-ivory p-6">
        <p className="eyebrow">Posts analyzed</p>
        <p className="mt-4 font-serif text-[40px] leading-[48px] text-ink">{(query.post_count ?? 0).toLocaleString()}</p>
      </section>
      <section className="card-ivory p-6">
        <p className="eyebrow">Positive sentiment</p>
        <p className="mt-4 font-serif text-[40px] leading-[48px] text-positive">{percent(query.positive_share)}</p>
      </section>
    </div>
  );
}
