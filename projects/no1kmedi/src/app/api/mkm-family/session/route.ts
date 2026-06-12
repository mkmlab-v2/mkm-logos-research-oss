import { NextRequest, NextResponse } from "next/server";

import { findAccountById, listProductLinks } from "@/lib/mkmFamilyAccountStoreV1";
import { mkmFamilyGoogleAuthEnabled } from "@/lib/mkmFamilyAuthConfigV1";
import { readSessionFromRequest } from "@/lib/mkmFamilyHttpV1";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  if (!mkmFamilyGoogleAuthEnabled()) {
    return NextResponse.json({
      ok: true,
      configured: false,
      authenticated: false,
    });
  }

  const session = readSessionFromRequest(request);
  if (!session) {
    return NextResponse.json({
      ok: true,
      configured: true,
      authenticated: false,
    });
  }

  const account = await findAccountById(session.sub);
  const links = (await listProductLinks()).filter((l) => l.mkm_account_id === session.sub);

  return NextResponse.json({
    ok: true,
    configured: true,
    authenticated: true,
    account: account
      ? {
          mkm_account_id: account.mkm_account_id,
          email: account.email,
          display_name: account.display_name,
          picture_url: account.picture_url,
        }
      : { mkm_account_id: session.sub, email: session.email },
    product_links: links.map((l) => ({
      product: l.product,
      product_profile_id: l.product_profile_id,
      linked_at_utc: l.linked_at_utc,
    })),
  });
}
