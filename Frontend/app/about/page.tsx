import type { Metadata } from "next";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return <AppShell active="/about"><article className="mx-auto max-w-3xl"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">About SentiBoard</p><h1 className="mt-3 font-serif text-4xl">A clearer view of feedback.</h1><p className="mt-5 text-base leading-7 text-muted">SentiBoard helps teams organize and understand sentiment in text, reviews, and online conversations.</p><section className="mt-8 rounded-xl border border-black/[0.06] bg-white p-6"><h2 className="font-serif text-2xl">Privacy and security</h2><p className="mt-3 text-sm leading-6 text-muted">Workspace data and account policies will be documented here.</p></section></article></AppShell>;
}
