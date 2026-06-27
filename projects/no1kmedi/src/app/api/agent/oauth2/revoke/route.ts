import { NextRequest, NextResponse } from "next/server";

import { verifyLogosAgentAccessToken } from "@/lib/logosAgentAuthJwtV1";
import { revokeJti } from "@/lib/logosAgentAuthStoreV1";

export const runtime = "nodejs";

async function parseBody(request: NextRequest): Promise<Record<string, string>> {
  const contentType = request.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const json = (await request.json()) as Record<string, string>;
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(json)) {
      if (typeof v === "string") out[k] = v;
    }
    return out;
  }
  const text = await request.text();
  const params = new URLSearchParams(text);
  const out: Record<string, string> = {};
  for (const [k, v] of params.entries()) out[k] = v;
  return out;
}

export async function POST(request: NextRequest) {
  try {
    const body = await parseBody(request);
    const token = (body.token || "").trim();
    if (!token) {
      return NextResponse.json({ error: "token_required" }, { status: 400 });
    }

    const claims = verifyLogosAgentAccessToken(token);
    if (!claims) {
      return NextResponse.json({ error: "invalid_token" }, { status: 400 });
    }

    await revokeJti(claims.jti);
    return NextResponse.json({ revoked: true, jti: claims.jti });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
