import Link from "next/link";
import type { ReactNode } from "react";
import { Brand } from "@/components/auth/AuthFrame";

const links = [
  { href: "/analyze", label: "Analyze" },
  { href: "/history", label: "History" },
  { href: "/about", label: "About" },
];

export default function AppShell({ children, active }: { children: ReactNode; active?: string }) {
  return (
    <div className="min-h-screen bg-paper text-ink md:flex">
      <aside className="flex w-full flex-col border-b border-black/[0.07] bg-[#f6f2e9] md:min-h-screen md:w-64 md:border-b-0 md:border-r">
        <div className="flex h-[72px] items-center border-b border-black/[0.07] px-6"><Brand /></div>
        <nav aria-label="Main navigation" className="flex gap-2 overflow-x-auto p-3 md:flex-col md:py-6">
          {links.map((link) => <Link key={link.href} href={link.href} aria-current={active === link.href ? "page" : undefined} className={`rounded-md px-4 py-3 text-sm font-medium ${active === link.href ? "bg-ink text-white" : "text-ink/75 hover:bg-white"}`}>{link.label}</Link>)}
        </nav>
        <div className="mt-auto hidden border-t border-black/[0.07] p-5 text-xs leading-5 text-muted md:block">SentiBoard<br />Qualitative research workspace</div>
      </aside>
      <main className="w-full flex-1 px-5 py-8 sm:px-8 lg:px-12">{children}</main>
    </div>
  );
}
