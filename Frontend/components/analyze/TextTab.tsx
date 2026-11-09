"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import ResultCard from "@/components/analyze/ResultCard";
import { ArrowRightIcon, SearchIcon } from "@/components/icons";
import { ErrorState, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { modelLabel } from "@/lib/format";
import type { AnalyzeResponse } from "@/lib/types";

const MAX_CHARS = 5000; // AnalyzeRequest.text max_length

export default function TextTab() {
  const [text, setText] = useState("");
  const [compare, setCompare] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState<AnalyzeResponse | null>(null);
  const [analyzedText, setAnalyzedText] = useState("");

  const trimmed = text.trim();
  const tooLong = text.length > MAX_CHARS;

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!trimmed || tooLong || loading) return;
    setLoading(true);
    setError("");
    try {
      const result = await api.analyzeText(text, compare);
      setResponse(result);
      setAnalyzedText(text);
    } catch (err) {
      setResponse(null);
      setError(err instanceof Error ? err.message : "We could not analyze this text.");
    } finally {
      setLoading(false);
    }
  };

  const [primary, comparison] = response?.results ?? [];
  const agree = primary && comparison ? primary.label === comparison.label : null;

  return (
    <div className="mx-auto max-w-[960px]">
      <form onSubmit={submit} className="card p-5 sm:p-10">
        <label htmlFor="analyze-text" className="sr-only">Text to analyze</label>
        <textarea
          id="analyze-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(); }}
          placeholder="Paste a review, comment or message…"
          rows={9}
          aria-invalid={tooLong}
          aria-describedby="analyze-text-help"
          className="block min-h-[220px] w-full resize-y rounded-md border border-transparent bg-sand/80 px-5 py-5 font-serif text-body-lg text-ink outline-none placeholder:text-charcoal/80 focus:border-accent focus:bg-white sm:px-7 sm:py-6"
        />
        <div id="analyze-text-help" className="mt-2 flex justify-between text-label-md font-normal text-muted">
          <span>Tip: press ⌘/Ctrl + Enter to analyze.</span>
          <span className={tooLong ? "font-semibold text-negative" : ""}>{text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}</span>
        </div>

        <div className="mt-8 flex flex-col-reverse gap-5 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex cursor-pointer items-start gap-3 text-sm text-charcoal">
            <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} className="mt-0.5 size-4 rounded-sm border-line-strong accent-ink" />
            <span>
              <span className="font-medium text-ink">Compare models</span>
              <span className="block text-label-md font-normal text-muted">Also run the second registered model (e.g. baseline) side by side.</span>
            </span>
          </label>
          <button type="submit" disabled={!trimmed || tooLong || loading} className="btn-primary min-h-12 px-8 text-base sm:min-w-[280px]">
            {loading ? <Spinner /> : <SearchIcon className="size-5" />}
            {loading ? "Reading…" : "Analyze sentiment"}
          </button>
        </div>
      </form>

      <div aria-live="polite" className="mt-8 space-y-6">
        {error && <ErrorState title="We could not analyze this text" message={error} onRetry={() => submit()} />}

        {response && primary && (
          <section aria-label="Result" className="space-y-5">
            <blockquote className="border-l-2 border-line-strong pl-5 font-serif text-quote italic text-charcoal">
              “{analyzedText.length > 280 ? `${analyzedText.slice(0, 280).trimEnd()}…` : analyzedText}”
            </blockquote>
            <div className={`grid gap-5 ${comparison ? "md:grid-cols-2" : ""}`}>
              <ResultCard result={primary} />
              {comparison && <ResultCard result={comparison} primary={false} />}
            </div>
            {agree !== null && (
              <p className="rounded-md bg-sage/50 px-4 py-3 text-sm text-charcoal">
                {agree
                  ? `Both models agree: ${primary.label}.`
                  : `The models disagree — ${modelLabel(primary.model)} reads ${primary.label}, ${modelLabel(comparison.model)} reads ${comparison.label}. Nuanced text often splits models; read it yourself before acting on it.`}
              </p>
            )}
            <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
              <span>Saved to your history.</span>
              <Link href="/history" className="inline-flex items-center gap-1.5 font-medium text-ink hover:text-accent-deep">
                View history <ArrowRightIcon className="size-4" />
              </Link>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
