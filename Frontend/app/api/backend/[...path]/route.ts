import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";
import { backendErrorMessage } from "@/lib/auth-proxy";
import { AUTH_COOKIE_NAME, backendUrl } from "@/lib/server/backend";

/**
 * Authenticated pass-through to FastAPI.
 *
 * The JWT lives in an HttpOnly cookie, so client code calls `/api/backend/<path>`
 * and this handler forwards the request with `Authorization: Bearer <token>`.
 * JSON, multipart (CSV upload) and file downloads (CSV export) all pass through.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Only these backend areas are reachable through the proxy.
const ALLOWED_ROOTS = new Set(["auth", "analyze", "queries", "models", "health"]);
const FORWARDED_RESPONSE_HEADERS = ["content-type", "content-disposition", "cache-control"];

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, { params }: Context) {
  const { path } = await params;
  if (!path.length || !ALLOWED_ROOTS.has(path[0]) || path.some((part) => part === ".." || part === ".")) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const url = backendUrl(path.map(encodeURIComponent).join("/"), request.nextUrl.search);
  if (!url) {
    return NextResponse.json({ detail: "The SentiBoard API is not configured (API_BASE_URL)." }, { status: 503 });
  }

  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const headers = new Headers({ Accept: request.headers.get("accept") ?? "application/json" });
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType); // keeps the multipart boundary
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const hasBody = !["GET", "HEAD"].includes(request.method);
  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "We could not reach the SentiBoard API. Is the backend running?" }, { status: 502 });
  }

  const responseHeaders = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }

  // Normalise error bodies to `{detail}` so the client has one shape to read.
  if (!upstream.ok && upstream.headers.get("content-type")?.includes("application/json")) {
    const payload: unknown = await upstream.json().catch(() => null);
    const response = NextResponse.json(
      { detail: backendErrorMessage(payload, upstream.statusText || "Request failed") },
      { status: upstream.status },
    );
    if (upstream.status === 401) response.cookies.delete(AUTH_COOKIE_NAME);
    return response;
  }

  const response = new NextResponse(upstream.status === 204 ? null : upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
  if (upstream.status === 401) response.cookies.delete(AUTH_COOKIE_NAME);
  return response;
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
