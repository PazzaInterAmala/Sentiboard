import { SENTIMENT_STYLE, SentimentChip } from "@/components/ui";
import { modelLabel, percent } from "@/lib/format";
import { SENTIMENTS, type Prediction } from "@/lib/types";

/** One model's verdict on one text: label, confidence and the three class probabilities. */
export default function ResultCard({ result, primary = true }: { result: Prediction; primary?: boolean }) {
  const style = SENTIMENT_STYLE[result.label];
  return (
    <article className="card-ivory p-6" aria-label={`${modelLabel(result.model)} result`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">{primary ? "Active model" : "Comparison model"} · {modelLabel(result.model)}</p>
          <p className={`mt-3 font-serif text-headline-lg ${style.text}`}>{style.label}</p>
          <p className="mt-1 text-sm text-muted">
            {percent(result.confidence)} confidence
            {result.confidence < 0.55 && <span className="text-charcoal"> · a borderline call, worth a second read</span>}
          </p>
        </div>
        <SentimentChip label={result.label} />
      </div>
      <hr className="my-5 border-line-strong" />
      <dl className="space-y-3">
        {SENTIMENTS.map((label) => {
          const value = result.probabilities[label] ?? 0;
          return (
            <div key={label} className="grid grid-cols-[80px_1fr_48px] items-center gap-3 text-sm">
              <dt className="text-charcoal">{SENTIMENT_STYLE[label].label}</dt>
              <dd className="h-2 overflow-hidden rounded-sm bg-sand">
                <span className={`block h-full ${SENTIMENT_STYLE[label].bar}`} style={{ width: `${value * 100}%` }} />
              </dd>
              <dd className="text-right tabular-nums text-ink">{percent(value)}</dd>
            </div>
          );
        })}
      </dl>
    </article>
  );
}
