"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { HistoryIcon } from "@/components/icons";
import { StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { percent, queryTitle, relativeTime } from "@/lib/format";
import type { Query, QueryType } from "@/lib/types";

/** Side panel listing the user's latest queries of one type. */
export default function RecentQueries({ type, title, intro }: { type: QueryType; title: string; intro: string }) {
  const [items, setItems] = useState<Query[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.listQueries(1, 50)
      .then((page) => !cancelled && setItems(page.items.filter((q) => q.type === type).slice(0, 3)))
      .catch(() => !cancelled && setFailed(true));
    return () => { cancelled = true; };
  }, [type]);

  return (
    <aside className="card p-6 sm:p-7">
      <div className="flex items-center justify-between">
        <p className="eyebrow">Your workspace</p>
        <HistoryIcon className="size-5 text-muted" />
      </div>
      <h2 className="mt-4 font-serif text-headline-md text-ink">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-charcoal">{intro}</p>

      <div className="mt-6 space-y-2">
        {items === null && !failed && [0, 1, 2].map((i) => <div key={i} className="h-[92px] animate-pulse rounded-md bg-sand/70" />)}
        {failed && <p className="text-sm text-muted">Recent queries could not be loaded.</p>}
        {items?.length === 0 && <p className="rounded-md bg-sand/70 px-4 py-5 text-sm text-muted">Nothing here yet. Your first analysis will appear here.</p>}
        {items?.map((query) => (
          <Link key={query.query_id} href={`/queries/${query.query_id}`} className="block rounded-md border border-transparent bg-sand/70 p-3.5 transition-colors hover:border-line hover:bg-sage/40">
            <div className="flex items-start justify-between gap-3">
              <p className="line-clamp-2 text-sm font-medium text-ink">{queryTitle(query)}</p>
              {query.status === "done" && query.positive_share !== null
                ? <span className="shrink-0 rounded border border-positive/25 bg-positive/[0.08] px-2 py-0.5 text-label-sm font-semibold text-positive">{percent(query.positive_share)} POS</span>
                : <StatusBadge status={query.status} />}
            </div>
            <div className="mt-2 flex justify-between text-label-md font-normal text-muted">
              <span>{query.post_count !== null ? `${query.post_count.toLocaleString()} posts` : "—"}</span>
              <span>{relativeTime(query.created_at)}</span>
            </div>
          </Link>
        ))}
      </div>
    </aside>
  );
}
