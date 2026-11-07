import type { Metadata } from "next";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = { title: "Analyze" };

export default function AnalyzePage() {
  return <AppShell active="/analyze"><div className="mx-auto max-w-4xl"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Analytical synthesis</p><h1 className="mt-3 font-serif text-4xl">Understand what people think.</h1><p className="mt-3 text-muted">Choose an input source to start a sentiment analysis.</p><section className="mt-8 rounded-xl border border-black/[0.06] bg-white p-6 sm:p-8"><div className="flex flex-wrap gap-2 border-b border-black/[0.06] pb-5">{["Text", "Reddit", "CSV upload"].map((item, index) => <button key={item} type="button" aria-pressed={index === 0} className={`rounded-md px-4 py-2 text-sm font-medium ${index === 0 ? "bg-ink text-white" : "bg-sand text-ink"}`}>{item}</button>)}</div><label htmlFor="analysis-text" className="sr-only">Text to analyze</label><textarea id="analysis-text" placeholder="Paste a review, comment, or message…" className="mt-5 min-h-52 w-full resize-y rounded-md bg-paper p-4 text-sm outline-none focus:ring-2 focus:ring-accent/20" /><div className="mt-4 flex justify-end"><button type="button" className="rounded-md bg-ink px-5 py-3 text-sm font-semibold text-white">Analyze sentiment →</button></div></section></div></AppShell>;
}
