/** Where to go after sign-in: the `?next=` path set by middleware, else Analyze. */
export function nextPath(fallback = "/analyze"): string {
  if (typeof window === "undefined") return fallback;
  const next = new URLSearchParams(window.location.search).get("next");
  // Same-origin paths only (no "//host" or absolute URLs).
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") ? next : fallback;
}
