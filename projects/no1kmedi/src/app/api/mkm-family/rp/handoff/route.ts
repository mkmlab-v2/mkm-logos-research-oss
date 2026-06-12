import { NextRequest, NextResponse } from "next/server";

import type { MkmFamilyRpProduct } from "@/lib/mkmFamilyAuthConfigV1";
import { mkmFamilyPublicOrigin, mkmFamilyRpOrigin } from "@/lib/mkmFamilyAuthConfigV1";
import { createHandoffCode } from "@/lib/mkmFamilyAccountStoreV1";
import { readSessionFromRequest, requireMkmFamilyAuthConfigured } from "@/lib/mkmFamilyHttpV1";

export const runtime = "nodejs";

function parseProduct(raw: string | null): MkmFamilyRpProduct | null {
  if (raw === "mkmlife" || raw === "personadiary") return raw;
  return null;
}

export async function GET(request: NextRequest) {
  const blocked = requireMkmFamilyAuthConfigured();
  if (blocked) return blocked;

  const session = readSessionFromRequest(request);
  if (!session) {
    const product = parseProduct(request.nextUrl.searchParams.get("product"));
    const login = new URL("/api/mkm-family/auth/google", mkmFamilyPublicOrigin());
    if (product) login.searchParams.set("return_to", `/api/mkm-family/rp/handoff?product=${product}`);
    return NextResponse.redirect(login.toString());
  }

  const product = parseProduct(request.nextUrl.searchParams.get("product"));
  if (!product) {
    return NextResponse.json({ ok: false, error: "product_required" }, { status: 400 });
  }

  const handoff = await createHandoffCode(session.sub, session.email, product);
  const origin = mkmFamilyRpOrigin(product);
  const redirectUrl = `${origin}/auth/mkm-callback?mkm_handoff=${encodeURIComponent(handoff.code)}`;

  if (request.nextUrl.searchParams.get("json") === "1") {
    return NextResponse.json({
      ok: true,
      product,
      redirect_url: redirectUrl,
      product_profile_id: handoff.product_profile_id,
    });
  }

  return NextResponse.redirect(redirectUrl);
}
