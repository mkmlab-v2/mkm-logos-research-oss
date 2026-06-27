import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";
import { loadPatientIntakeSendGate } from "@/lib/patient-intake-send-gate-v1";

function loadTemplates(): Record<string, unknown> | null {
  const candidates = [
    path.join(process.cwd(), "memory/commercialization/patient_intake_notification_templates_v1.json"),
    path.join(process.cwd(), "../../docs/final/artifacts/patient_intake_notification_templates_v1.json"),
  ];
  for (const candidate of candidates) {
    try {
      if (!fs.existsSync(candidate)) continue;
      return JSON.parse(fs.readFileSync(candidate, "utf8")) as Record<string, unknown>;
    } catch {
      // try next
    }
  }
  return null;
}

function render(body: string, variables: Record<string, string>): string {
  let out = body;
  for (const [key, value] of Object.entries(variables)) {
    out = out.replaceAll(`{${key}}`, value);
  }
  return out;
}

export async function GET() {
  const gate = loadPatientIntakeSendGate();
  const doc = loadTemplates();
  if (!doc) {
    return NextResponse.json({ success: false, error: "templates_not_found" }, { status: 404 });
  }

  const intakeUrl = String(doc.intake_url_default || "https://jema-ai.com/intake");
  const vars = { intake_url: intakeUrl, clinic_name: "한의원", intake_pin: "ABC-123" };
  const templates = (doc.templates || {}) as Record<string, { channel?: string; body?: string }>;
  const rendered: Record<string, { channel: string; body: string }> = {};
  for (const [key, tpl] of Object.entries(templates)) {
    rendered[key] = {
      channel: String(tpl.channel || "sms_lms"),
      body: render(String(tpl.body || ""), vars),
    };
  }

  return NextResponse.json(
    {
      success: true,
      send_gate: gate.send_gate,
      ready_internal_poc: gate.ready_internal_poc,
      ready_for_external_send: gate.ready_for_external_send,
      intake_url: intakeUrl,
      paste_assistant_path: "/demo/patient_intake_paste_assistant_v1.html",
      templates: rendered,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
