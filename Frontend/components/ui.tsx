import Link from "next/link";
import type { ReactNode } from "react";
import { AlertIcon, RefreshIcon } from "@/components/icons";
import { percent } from "@/lib/format";
import type { QueryStatus, Sentiment } from "@/lib/types";

/** Sentiment colours are identical everywhere (plan §8.3, DESIGN.md). */
export const SENTIMENT_STYLE: Record<Sentiment, { label: string; hex: string; chip: string; bar: string; text: string }> = {
  positive: { label: "Positive", hex: "#3D7A5A", chip: "border-positive/25 bg-positive/[0.08] text-positive", bar: "bg-positive", text: "text-positive" },
  neutral: { label: "Neutral", hex: "#8A9BA8", chip: "border-neutral/30 bg-neutral/10 text-[#5E6A75]", bar: "bg-neutral", text: "text-[#5E6A75]" },
  negative: { label: "Negative", hex: "#BA4A4A", chip: "border-negative/25 bg-negative/[0.08] text-negative", bar: "bg-negative", text: "text-negative" },
};

export function SentimentChip({ label, children }: { label: Sentiment; children?: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded border px-2.5 py-1 text-label-sm font-semibold uppercase ${SENTIMENT_STYLE[label].chip}`}>
      {children ?? SENTIMENT_STYLE[label].label}
    </span>
  );
}

const STATUS_STYLE: Record<QueryStatus, { label: string; className: string; dot: string }> = {
  done: { label: "Completed", className: "border-positive/20 bg-positive/[0.07] text-positive", dot: "bg-positive" },
  processing: { label: "Processing", className: "border-accent/20 bg-accent/[0.07] text-accent-deep", dot: "bg-accent" },
  pending: { label: "Queued", className: "border-accent/20 bg-accent/[0.05] text-accent-deep", dot: "bg-accent/60" },
  failed: { label: "Failed", className: "border-negative/20 bg-negative/[0.07] text-negative", dot: "bg-negative" },
};

export function StatusBadge({ status, positiveShare }: { status: QueryStatus; positiveShare?: number | null }) {
  const style = STATUS_STYLE[status];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded border px-2.5 py-1 text-label-md font-medium ${style.className}`}>
      <span aria-hidden="true" className={`size-1.5 rounded-full ${style.dot}`} />
      {style.label}
      {status === "done" && positiveShare !== null && positiveShare !== undefined && <> · {percent(positiveShare)} Positive</>}
    </span>
  );
}

/** Horizontal split bar positive / neutral / negative. */
export function DistributionBar({ split, className = "h-2.5" }: { split: Record<Sentiment, number>; className?: string }) {
  const order: Sentiment[] = ["positive", "neutral", "negative"];
  return (
    <div className={`flex w-full overflow-hidden rounded-sm bg-sand ${className}`} role="img" aria-label={order.map((s) => `${SENTIMENT_STYLE[s].label} ${percent(split[s])}`).join(", ")}>
      {order.map((s) => split[s] > 0 && <span key={s} className={SENTIMENT_STYLE[s].bar} style={{ width: `${split[s] * 100}%` }} />)}
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, aside }: { eyebrow?: ReactNode; title: ReactNode; description?: ReactNode; aside?: ReactNode }) {
  return (
    <header className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
      <div className="max-w-3xl">
        {eyebrow && <p className="eyebrow mb-3">{eyebrow}</p>}
        <h1 className="font-serif text-display-md text-ink md:text-display-lg">{title}</h1>
        {description && <p className="mt-2 font-serif text-body-lg text-charcoal">{description}</p>}
      </div>
      {aside}
    </header>
  );
}

export function Spinner({ className = "size-4" }: { className?: string }) {
  return <span aria-hidden="true" className={`inline-block animate-spin rounded-full border-2 border-current border-t-transparent ${className}`} />;
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="card-ivory px-6 py-12 text-center">
      <h2 className="font-serif text-headline-sm text-ink">{title}</h2>
      {children && <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{children}</p>}
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", message, onRetry, action }: { title?: string; message: string; onRetry?: () => void; action?: ReactNode }) {
  return (
    <div role="alert" className="rounded-md border border-negative/25 bg-negative/[0.04] px-5 py-4">
      <div className="flex gap-3">
        <AlertIcon className="mt-0.5 size-5 shrink-0 text-negative" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink">{title}</p>
          <p className="mt-1 text-sm leading-6 text-charcoal">{message}</p>
          {(onRetry || action) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {onRetry && <button type="button" onClick={onRetry} className="btn-ghost min-h-9 px-3 py-1.5"><RefreshIcon className="size-4" /> Try again</button>}
              {action}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Shown when the frontend calls a planned backend route that is not deployed yet. */
export function NotAvailableNotice({ feature }: { feature: string }) {
  return (
    <div className="rounded-md border border-line bg-sand px-5 py-4 text-sm leading-6 text-charcoal">
      <span className="font-semibold text-ink">{feature} is not available on the API yet.</span> The screen is ready and will work once the backend exposes this endpoint.
    </div>
  );
}

export function TextLink({ href, children }: { href: string; children: ReactNode }) {
  return <Link href={href} className="font-medium text-accent-deep underline-offset-4 hover:underline">{children}</Link>;
}
