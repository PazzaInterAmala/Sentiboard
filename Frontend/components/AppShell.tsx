"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Brand } from "@/components/Brand";
import { AboutIcon, AnalyzeIcon, HistoryIcon, LogoutIcon, UserIcon } from "@/components/icons";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

const links = [
  { href: "/analyze", label: "Analyze", icon: AnalyzeIcon, match: ["/analyze", "/queries"] },
  { href: "/history", label: "History", icon: HistoryIcon, match: ["/history"] },
  { href: "/about", label: "About", icon: AboutIcon, match: ["/about"] },
];

function useCurrentUser() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  useEffect(() => {
    let cancelled = false;
    api.me().then((me) => !cancelled && setUser(me)).catch(() => !cancelled && setUser(null));
    return () => { cancelled = true; };
  }, []);
  return user;
}

function Avatar({ className = "size-10" }: { className?: string }) {
  return <span className={`grid shrink-0 place-items-center rounded-lg bg-ink text-ivory ${className}`}><UserIcon className="size-[18px]" /></span>;
}

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const user = useCurrentUser();
  const [signingOut, setSigningOut] = useState(false);

  const signOut = async () => {
    setSigningOut(true);
    await api.logout().catch(() => undefined);
    router.replace("/login");
    router.refresh();
  };

  const isActive = (match: string[]) => match.some((m) => pathname === m || pathname.startsWith(`${m}/`));

  return (
    <div className="min-h-screen bg-paper text-ink md:flex">
      <aside className="border-b border-line bg-sand md:sticky md:top-0 md:flex md:h-screen md:w-[260px] md:shrink-0 md:flex-col md:border-b-0 md:border-r lg:w-[300px]">
        <div className="flex h-16 items-center justify-between border-b border-line px-5 md:h-20 md:px-7">
          <Brand />
          <div className="md:hidden">
            {user ? (
              <button type="button" onClick={signOut} disabled={signingOut} className="btn-quiet min-h-9 text-sm" aria-label="Sign out"><LogoutIcon className="size-5" /></button>
            ) : user === null ? <Link href="/login" className="text-sm font-medium text-accent-deep">Sign in</Link> : null}
          </div>
        </div>
        <nav aria-label="Main navigation" className="flex gap-1 overflow-x-auto px-3 py-2 md:flex-col md:gap-1.5 md:px-3 md:py-7">
          {links.map(({ href, label, icon: Icon, match }) => {
            const active = isActive(match);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex shrink-0 items-center gap-3 rounded-md px-4 py-2.5 text-[15px] transition-colors duration-150 md:py-3 ${active ? "bg-ink text-ivory" : "text-charcoal hover:bg-ivory hover:text-ink"}`}
              >
                <Icon className={`size-5 ${active ? "text-ivory/70" : ""}`} />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto hidden items-center gap-3 border-t border-line px-5 py-5 md:flex">
          {user === undefined ? (
            <div className="h-10 w-full animate-pulse rounded-md bg-ivory" aria-hidden="true" />
          ) : user ? (
            <>
              <Avatar />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[15px] text-ink">{user.username}</p>
                <p className="truncate text-label-md font-normal text-muted">{user.email}</p>
              </div>
              <button type="button" onClick={signOut} disabled={signingOut} className="rounded-md p-2 text-charcoal hover:bg-ivory hover:text-ink" aria-label="Sign out" title="Sign out">
                <LogoutIcon className="size-5" />
              </button>
            </>
          ) : (
            <Link href="/login" className="btn-primary w-full">Sign in</Link>
          )}
        </div>
      </aside>
      <main className="min-w-0 flex-1">
        <div className="mx-auto w-full max-w-content px-5 pb-16 pt-8 sm:px-8 lg:px-12 lg:pt-12">{children}</div>
      </main>
    </div>
  );
}
