import { NextResponse } from "next/server";

import { clearSessionCookie } from "@/lib/mkmFamilyHttpV1";

export const runtime = "nodejs";

export async function POST() {
  const res = NextResponse.json({ ok: true });
  clearSessionCookie(res);
  return res;
}
