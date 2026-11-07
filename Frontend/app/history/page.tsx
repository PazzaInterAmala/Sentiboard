import type { Metadata } from "next";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = { title: "History" };

export default function HistoryPage() {
  return <AppShell active="/history"><div className="mx-auto max-w-5xl"><div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="font-serif text-4xl">History</h1><p className="mt-2 text-muted">Past sentiment analyses and reviews.</p></div><a href="/analyze" className="rounded-md bg-ink px-4 py-3 text-sm font-semibold text-white">＋ New analysis</a></div><div className="mt-8 rounded-xl border border-black/[0.06] bg-white p-6"><label htmlFor="history-search" className="sr-only">Search past analyses</label><input id="history-search" placeholder="Search past analyses…" className="w-full max-w-md rounded-md bg-paper px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-accent/20" /><div className="mt-6 border-t border-black/[0.06] py-8 text-center text-sm text-muted">Analysis records will be loaded from the history API.</div></div></div></AppShell>;
}
