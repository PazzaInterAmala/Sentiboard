import { NextResponse } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/server/backend";

export const runtime = "nodejs";

export function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(AUTH_COOKIE_NAME);
  return response;
}
