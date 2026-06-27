import { NextRequest, NextResponse } from "next/server";

import {
  registerServiceAuth,
  requestOrigin,
} from "@/lib/logosAgentAuthV1";

export const runtime = "nodejs";

type IdentityBody = {
  type?: string;
  login_hint?: string;
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as IdentityBody;
    const type = (body.type || "").trim();

    if (type === "identity_assertion") {
      return NextResponse.json(
        { error: "identity_assertion_not_enabled" },
        { status: 400 },
      );
    }
    if (type === "anonymous") {
      return NextResponse.json({ error: "anonymous_not_enabled" }, { status: 400 });
    }
    if (type !== "service_auth") {
      return NextResponse.json({ error: "unsupported_identity_type" }, { status: 400 });
    }

    const loginHint = (body.login_hint || "").trim();
    if (!loginHint) {
      return NextResponse.json({ error: "login_hint_required" }, { status: 400 });
    }

    const result = await registerServiceAuth({
      login_hint: loginHint,
      origin: requestOrigin(request.headers),
    });
    return NextResponse.json(result.body, { status: result.ok ? 200 : result.status });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
