/** Where to go after sign-in: the `?next=` path set by middleware, else Analyze. */
export function nextPath(fallback = "/analyze"): string {
  if (typeof window === "undefined") return fallback;
  const next = new URLSearchParams(window.location.search).get("next");
  if (!next || !next.startsWith("/")) return fallback;
  // Resolve the way the browser will: "/\evil.com" passes a string check but becomes
  // "https://evil.com/", so compare origins instead of prefixes.
  const url = new URL(next, window.location.origin);
  if (url.origin !== window.location.origin || url.pathname.startsWith("/login")) return fallback;
  return url.pathname + url.search + url.hash;
}
