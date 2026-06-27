import { NextRequest, NextResponse } from "next/server";
import type { ClinicianChatThread } from "@/lib/clinician-chat-types";
import { normalizeClinicianThreads } from "@/lib/clinician-chat-storage";
import { clinicianEmailFromRequest, resolveClinicianProAccess } from "@/lib/clinician-access-server-v1";
import {
  getClinicianThreadsForEmail,
  saveClinicianThreadsForEmail,
} from "@/lib/clinician-threads-store-server";

export const runtime = "nodejs";

async function requireProEmail(request: NextRequest) {
  const email = clinicianEmailFromRequest(request);
  if (!email) {
    return {
      ok: false as const,
      response: NextResponse.json({ success: false, error: "email_required" }, { status: 400 }),
    };
  }
  const access = await resolveClinicianProAccess(email);
  if (!access.unlocked) {
    return {
      ok: false as const,
      response: NextResponse.json(
        {
          success: false,
          error: "pro_clinical_assist_required",
          payment_status: access.payment_status,
          verification_status: access.verification_status,
        },
        { status: 403 },
      ),
    };
  }
  return { ok: true as const, email, access };
}

export async function GET(request: NextRequest) {
  try {
    const gate = await requireProEmail(request);
    if (!gate.ok) return gate.response;
    const threads = await getClinicianThreadsForEmail(gate.email);
    return NextResponse.json(
      {
        success: true,
        email: gate.email,
        threads,
        count: threads.length,
        sync_source: gate.access.access_source,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "threads_get_failed";
    return NextResponse.json({ success: false, error: msg }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const gate = await requireProEmail(request);
    if (!gate.ok) return gate.response;
    const body = (await request.json()) as { threads?: ClinicianChatThread[] };
    const threads = normalizeClinicianThreads({ v: 1, threads: body.threads ?? [] });
    const saved = await saveClinicianThreadsForEmail(gate.email, threads);
    return NextResponse.json(
      {
        success: true,
        email: gate.email,
        threads,
        savedAt: saved.savedAt,
        count: saved.count,
        sync_source: gate.access.access_source,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "threads_put_failed";
    return NextResponse.json({ success: false, error: msg }, { status: 500 });
  }
}
