import type { Metadata } from "next";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return <AppShell><div className="mx-auto max-w-5xl"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Workspace overview</p><h1 className="mt-3 font-serif text-4xl">Your insights</h1><p className="mt-3 text-muted">Your sentiment analyses and recent activity will appear here.</p><div className="mt-8 grid gap-4 sm:grid-cols-3">{["Total analyses", "Opinions reviewed", "Positive sentiment"].map((label) => <section key={label} className="rounded-xl border border-black/[0.06] bg-white p-6"><p className="text-sm text-muted">{label}</p><p className="mt-4 font-serif text-3xl">—</p></section>)}</div><section className="mt-6 rounded-xl border border-black/[0.06] bg-white p-6"><h2 className="font-serif text-2xl">Recent analyses</h2><p className="mt-3 text-sm text-muted">Connect this view to the analysis history API.</p></section></div></AppShell>;
}
