import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRightIcon, InfoIcon, RefreshIcon } from "@/components/icons";

export const metadata: Metadata = { title: "About" };

const steps = [
  { title: "Bring the words", body: "Paste a single comment, search Reddit for a keyword, or upload a CSV of reviews or survey answers." },
  { title: "Read every phrase", body: "A fine-tuned DistilBERT model reads each text and estimates whether it is positive, neutral or negative, with a confidence score." },
  { title: "See the pattern", body: "Results roll up into a sentiment split, a trend over time, the words that recur in each tone, and the posts behind them." },
];

export default function AboutPage() {
  return (
    <article className="mx-auto max-w-[960px] py-4 lg:py-6">
      <p className="text-label-md font-semibold uppercase text-accent-deep">About the platform</p>
      <h1 className="mt-4 font-serif text-display-md text-ink md:text-[56px] md:leading-[64px] md:tracking-[-0.02em]">How SentiBoard works</h1>
      <p className="mt-6 max-w-[62ch] font-serif text-[20px] leading-[34px] text-charcoal md:text-[22px] md:leading-[38px]">
        A quiet, thoughtful companion designed to help anyone understand how people truly feel about a topic, product, or brand—without requiring a background in data science or engineering.
      </p>

      <hr className="my-12 border-line md:my-16" />

      <section aria-labelledby="synthesis">
        <h2 id="synthesis" className="font-serif text-headline-md text-ink md:text-[28px] md:leading-9">Clear synthesis, not raw complexity</h2>
        <p className="mt-4 max-w-[70ch] font-serif text-body-lg text-charcoal md:text-[19px] md:leading-[34px]">
          Instead of overwhelming you with tangled code or superficial keyword counts, SentiBoard reads complete phrases and qualitative feedback. It brings forward prevailing sentiment, highlights the words that recur in praise and in complaints, and shows you the voices behind every number.
        </p>

        <ol className="mt-10 grid gap-px overflow-hidden rounded-md border border-line bg-line md:grid-cols-3">
          {steps.map((step, index) => (
            <li key={step.title} className="bg-ivory p-6">
              <p className="text-label-md font-semibold text-muted">0{index + 1}</p>
              <h3 className="mt-3 font-serif text-headline-sm text-ink">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 text-charcoal">{step.body}</p>
            </li>
          ))}
        </ol>

        <aside className="mt-10 rounded-md border border-line bg-sand/70 p-6 md:p-8">
          <h3 className="flex items-center gap-2 text-[17px] font-semibold text-ink">
            <InfoIcon className="size-5 text-accent-deep" /> Understanding model estimates
          </h3>
          <p className="mt-3 text-[15px] leading-7 text-charcoal">
            Sentiment predictions are statistical estimates rather than infallible truths. Nuanced language—such as sarcasm, cultural idioms, irony, and complex context—can occasionally confound automated models. We recommend pairing SentiBoard&apos;s overviews with firsthand review whenever crucial decisions depend on subtle judgment.
          </p>
        </aside>
      </section>

      <div className="mt-14 flex flex-wrap items-center gap-6">
        <Link href="/analyze" className="btn-primary min-h-12 px-6 text-base">Start an analysis <ArrowRightIcon className="size-5" /></Link>
        <Link href="/history" className="inline-flex items-center gap-2 text-base text-ink hover:text-accent-deep"><RefreshIcon className="size-5" /> View history</Link>
      </div>
    </article>
  );
}
