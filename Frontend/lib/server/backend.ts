/** FastAPI origin. Read only on the server; the browser never talks to FastAPI directly. */
export function backendBaseUrl(): string | null {
  const baseUrl = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) return null;
  return baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
}

export function backendUrl(path: string, search = ""): URL | null {
  const base = backendBaseUrl();
  if (!base) return null;
  const url = new URL(path.replace(/^\/+/, ""), base);
  url.search = search;
  return url;
}

export const AUTH_COOKIE_NAME = process.env.AUTH_COOKIE_NAME || "sentiboard_session";

export function authCookieMaxAge(): number {
  const configured = Number(process.env.AUTH_COOKIE_MAX_AGE_SECONDS);
  return Number.isFinite(configured) && configured > 0 ? configured : 60 * 60 * 24;
}
