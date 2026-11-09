"use client";

import { useEffect, useState } from "react";
import { SENTIMENT_STYLE } from "@/components/ui";
import { api } from "@/lib/api";
import { percent } from "@/lib/format";
import { SENTIMENTS, type PostWithPrediction, type Sentiment } from "@/lib/types";

/**
 * "What people are saying": the 2 most confident posts per class
 * (the model cannot summarise themes, plan §8.5). Hidden if posts are unavailable.
 */
export default function ExamplePosts({ queryId }: { queryId: number }) {
  const [examples, setExamples] = useState<Record<Sentiment, PostWithPrediction[]> | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all(SENTIMENTS.map((label) => api.getPosts(queryId, 1, 50, label).then((page) => page.items)))
      .then((lists) => {
        if (cancelled) return;
        const top = (items: PostWithPrediction[]) => [...items].sort((a, b) => b.prediction.confidence - a.prediction.confidence).slice(0, 2);
        setExamples({ positive: top(lists[0]), neutral: top(lists[1]), negative: top(lists[2]) });
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [queryId]);

  if (!examples || SENTIMENTS.every((s) => examples[s].length === 0)) return null;

  return (
    <section aria-labelledby="examples-heading" className="mt-16">
      <h2 id="examples-heading" className="font-serif text-headline-md text-ink">What people are saying</h2>
      <p className="mt-1 text-sm text-muted">The posts the model was most confident about, by tone.</p>
      <div className="mt-6 grid gap-5 lg:grid-cols-3">
        {SENTIMENTS.map((label) => (
          <div key={label} className="space-y-4">
            <p className={`text-label-md font-semibold uppercase ${SENTIMENT_STYLE[label].text}`}>{SENTIMENT_STYLE[label].label}</p>
            {examples[label].length === 0 && <p className="text-sm text-muted">No {label} posts.</p>}
            {examples[label].map((post) => (
              <figure key={post.post_id} className="card-ivory p-6">
                <blockquote className="line-clamp-6 font-serif text-[18px] leading-[28px] text-ink">“{post.text}”</blockquote>
                <figcaption className="mt-4 flex justify-between border-t border-line-strong pt-3 text-label-md font-normal text-muted">
                  <span>{post.author ? `u/${post.author}` : post.subreddit ? `r/${post.subreddit}` : "Anonymous"}</span>
                  <span>{percent(post.prediction.confidence)} confidence</span>
                </figcaption>
              </figure>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
