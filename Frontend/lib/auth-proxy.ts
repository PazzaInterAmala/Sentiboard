import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME, authCookieMaxAge, backendUrl } from "@/lib/server/backend";

type AuthKind = "login" | "register";

function authPath(kind: AuthKind): string {
  return kind === "login"
    ? process.env.API_AUTH_LOGIN_PATH || "/auth/login"
    : process.env.API_AUTH_REGISTER_PATH || "/auth/register";
}

export function backendErrorMessage(payload: unknown, fallback = "We could not complete your request. Please try again."): string {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    const detail = record.detail ?? record.message ?? record.error;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const messages = detail.map((item) => item && typeof item === "object" && "msg" in item ? String(item.msg) : "").filter(Boolean);
      if (messages.length) return messages.join(" ");
    }
  }
  return fallback;
}

export async function proxyAuthRequest(request: Request, kind: AuthKind) {
  const url = backendUrl(authPath(kind));
  if (!url) {
    return NextResponse.json({ message: "Authentication service is not configured." }, { status: 503 });
  }

  let credentials: unknown;
  try {
    credentials = await request.json();
  } catch {
    return NextResponse.json({ message: "Submit valid JSON credentials." }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(credentials),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ message: "Could not reach the authentication service." }, { status: 502 });
  }

  const payload: unknown = await upstream.json().catch(() => null);
  if (!upstream.ok) {
    return NextResponse.json({ message: backendErrorMessage(payload) }, { status: upstream.status });
  }

  const record = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
  const token = typeof record.token === "string" ? record.token : typeof record.access_token === "string" ? record.access_token : undefined;
  if (!token) {
    return NextResponse.json({ message: "The authentication service returned an invalid response." }, { status: 502 });
  }

  const safePayload = { ...record };
  delete safePayload.token;
  delete safePayload.access_token;
  const response = NextResponse.json(safePayload, { status: upstream.status });
  response.cookies.set(AUTH_COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: authCookieMaxAge(),
  });
  return response;
}
