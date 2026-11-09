import Link from "next/link";

export function BrandMark({ className = "size-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={className}>
      <circle cx="16" cy="16" r="16" fill="#172B3A" />
      <path d="M11 21.5c-1.6-3.6.4-8.8 5.2-9.6 3.4-.6 5.6 1.8 5 4.3-.5 2.1-2.8 3-4.4 2" fill="none" stroke="#FAF8F5" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Brand({ href = "/analyze" }: { href?: string }) {
  return (
    <Link href={href} aria-label="SentiBoard home" className="inline-flex items-center gap-2 text-ink">
      <BrandMark />
      <span className="text-[17px] leading-none">
        <span className="font-serif font-semibold">Senti</span>
        <span className="font-sans text-accent">Board</span>
      </span>
    </Link>
  );
}
