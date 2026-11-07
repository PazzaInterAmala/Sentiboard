import Link from "next/link";
import type { ReactNode } from "react";

export function Brand() {
  return (
    <Link href="/" aria-label="SentiBoard home" className="inline-flex items-center gap-2 text-ink">
      <span className="grid size-7 place-items-center rounded bg-ink font-serif text-lg text-white">S</span>
      <span className="font-serif text-lg tracking-tight">SentiBoard</span>
    </Link>
  );
}

export function AuthFrame({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col bg-paper px-5 text-ink sm:px-8">
      <header className="flex h-[72px] items-center justify-between">
        <Brand />
        <Link className="text-xs font-medium text-ink/70 hover:text-ink sm:text-sm" href="/about">
          Inquiry &amp; Support ↗
        </Link>
      </header>
      <div className="flex flex-1 flex-col items-center justify-center py-8 sm:py-12">
        <div className="mb-5 grid size-10 place-items-center rounded-lg bg-ink font-serif text-xl text-white" aria-hidden="true">S</div>
        <p className="mb-2 rounded-full bg-sand px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">
          <span className="mr-1.5 inline-block size-1.5 rounded-full bg-accent align-middle" />Institutional archive &amp; dossiers
        </p>
        <h1 className="mb-2 text-center font-serif text-3xl tracking-tight sm:text-4xl">{title}</h1>
        <p className="mb-7 max-w-md text-center text-sm leading-6 text-muted sm:text-base">
          Understand how people feel about your products and qualitative ideas.
        </p>
        <section className="w-full max-w-[440px] rounded-xl border border-black/[0.04] bg-white p-6 shadow-[0_3px_10px_rgba(7,27,40,0.08)] sm:p-9">
          {children}
        </section>
        <p className="mt-5 max-w-md text-center text-xs leading-5 text-muted">
          Your account details are protected and used to manage your SentiBoard workspace.
        </p>
      </div>
      <footer className="flex min-h-[56px] flex-wrap items-center justify-between gap-3 py-4 text-[11px] text-muted">
        <span>© {new Date().getFullYear()} SentiBoard Qualitative Research</span>
        <nav aria-label="Legal" className="flex gap-4"><Link href="/about" className="hover:text-ink">Privacy</Link><Link href="/about" className="hover:text-ink">Terms</Link><Link href="/about" className="hover:text-ink">Security</Link></nav>
      </footer>
    </main>
  );
}

export function AuthTabs({ active }: { active: "login" | "register" }) {
  return (
    <div className="mb-6 grid grid-cols-2 rounded-md bg-sand p-1" aria-label="Authentication pages">
      <Link href="/login" aria-current={active === "login" ? "page" : undefined} className={`rounded px-3 py-2 text-center text-sm font-medium transition ${active === "login" ? "bg-white text-ink shadow-sm" : "text-muted hover:text-ink"}`}>Sign in</Link>
      <Link href="/register" aria-current={active === "register" ? "page" : undefined} className={`rounded px-3 py-2 text-center text-sm font-medium transition ${active === "register" ? "bg-white text-ink shadow-sm" : "text-muted hover:text-ink"}`}>Create account</Link>
    </div>
  );
}

export function FormAlert({ children }: { children: ReactNode }) {
  if (!children) return null;
  return <div role="alert" className="mb-5 rounded-md border border-red-200 bg-red-50 px-3.5 py-3 text-sm leading-5 text-red-800">{children}</div>;
}

export function FieldError({ children, id }: { children?: ReactNode; id: string }) {
  return children ? <p id={id} className="mt-1.5 text-xs font-medium text-red-700">{children}</p> : null;
}

export function SubmitButton({ loading, children }: { loading: boolean; children: ReactNode }) {
  return (
    <button type="submit" disabled={loading} className="mt-6 flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-ink px-4 py-3 text-sm font-semibold text-white transition hover:bg-ink/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-wait disabled:opacity-70">
      {loading && <span aria-hidden="true" className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
      <span>{loading ? "Please wait…" : children}</span>
      {!loading && <span aria-hidden="true">→</span>}
    </button>
  );
}
