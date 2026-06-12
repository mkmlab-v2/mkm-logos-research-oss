import { NextRequest, NextResponse } from "next/server";

import { consumeHandoffCode } from "@/lib/mkmFamilyAccountStoreV1";
import {
  corsPreflightResponse,
  requireMkmFamilyAuthConfigured,
  withCorsJson,
} from "@/lib/mkmFamilyHttpV1";

export const runtime = "nodejs";

export async function OPTIONS(request: NextRequest) {
  const origin = request.headers.get("origin");
  const preflight = corsPreflightResponse(origin);
  return preflight ?? new NextResponse(null, { status: 403 });
}

export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  const blocked = requireMkmFamilyAuthConfigured();
  if (blocked) return withCorsJson(origin, await blocked.json(), { status: 503 });

  let body: { code?: string };
  try {
    body = (await request.json()) as { code?: string };
  } catch {
    return withCorsJson(origin, { ok: false, error: "invalid_json" }, { status: 400 });
  }

  const code = (body.code || "").trim();
  if (!code) {
    return withCorsJson(origin, { ok: false, error: "code_required" }, { status: 400 });
  }

  const row = await consumeHandoffCode(code);
  if (!row) {
    return withCorsJson(origin, { ok: false, error: "invalid_or_expired_code" }, { status: 401 });
  }

  return withCorsJson(origin, {
    ok: true,
    mkm_account_id: row.mkm_account_id,
    email: row.email,
    product: row.product,
    product_profile_id: row.product_profile_id,
    federation_only: true,
    db_merge: false,
  });
}
