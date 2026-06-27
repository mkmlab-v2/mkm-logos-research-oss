/**
 * Myeongni Studio — verify-lite → mindmap input (B-track · NON_GATING · send_gate HOLD).
 */
import { NextResponse } from "next/server";

import {
  MYEONGNI_FULL_REPORT_SSOT,
  myeongniLiteRecordToMindmapInput,
} from "@/lib/myeongniLiteToMindmapInputV1";
import {
  runVerifyLiteEngine,
  type VerifyLiteBody,
} from "@/lib/manseryeok-verify-lite-engine";

type StudioBody = VerifyLiteBody & {
  query?: string;
};

function isInt(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function validateBody(body: StudioBody): string[] {
  const errors: string[] = [];
  const utc =
    typeof body.birth_instant_utc === "string" && body.birth_instant_utc.trim().length > 0;
  if (utc) {
    if (!/^\d{4}-\d{2}-\d{2}[T ]\d/.test(body.birth_instant_utc!.trim())) {
      errors.push("birth_instant_utc");
    }
  } else {
    if (!isInt(body.year)) errors.push("year");
    if (!isInt(body.month) || body.month! < 1 || body.month! > 12) errors.push("month");
    if (!isInt(body.day) || body.day! < 1 || body.day! > 31) errors.push("day");
    if (!isInt(body.hour) || body.hour! < 0 || body.hour! > 23) errors.push("hour");
    if (body.minute != null && (!isInt(body.minute) || body.minute < 0 || body.minute > 59)) {
      errors.push("minute");
    }
  }
  if (typeof body.tz !== "string" || body.tz.trim().length === 0) errors.push("tz");
  return errors;
}

export async function POST(req: Request) {
  let body: StudioBody;
  try {
    body = (await req.json()) as StudioBody;
  } catch {
    return NextResponse.json({ success: false, error: "invalid_json" }, { status: 400 });
  }

  const invalid = validateBody(body);
  if (invalid.length > 0) {
    return NextResponse.json(
      { success: false, error: "invalid_input", invalid_fields: invalid },
      { status: 400 },
    );
  }

  const query = typeof body.query === "string" ? body.query.trim() : "";

  try {
    const doc = await runVerifyLiteEngine(body);
    const lite = doc.myeongni_lite as Record<string, unknown> | null;
    const mindmap_input = myeongniLiteRecordToMindmapInput(query, lite);

    if (!mindmap_input) {
      return NextResponse.json(
        {
          success: false,
          error: "myeongni_lite_empty",
          gate_status: doc.gate_status,
          policy_interpretation: doc.policy_interpretation,
          reasons: doc.reasons,
        },
        { status: 422 },
      );
    }

    return NextResponse.json(
      {
        success: true,
        send_gate: "HOLD",
        research_only: true,
        non_gating: true,
        gate_status: doc.gate_status,
        policy_interpretation: doc.policy_interpretation,
        reasons: doc.reasons ?? [],
        boundary_warning:
          doc.gate_status === "REVIEW" ||
          (Array.isArray(doc.reasons) &&
            doc.reasons.some((r) => String(r).includes("boundary"))),
        mindmap_input,
        myeongni_lite_schema: lite?.schema ?? null,
        full_report_pointer: MYEONGNI_FULL_REPORT_SSOT,
        disclaimer_ko:
          typeof lite?.disclaimer_ko === "string"
            ? lite.disclaimer_ko
            : MYEONGNI_FULL_REPORT_SSOT.note_ko,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    const isRoot = msg.includes("workspace_root_not_found");
    return NextResponse.json(
      {
        success: false,
        error: isRoot ? "workspace_root_not_found" : "engine_runtime_error",
        message: msg.slice(0, 400),
      },
      { status: isRoot ? 503 : 500 },
    );
  }
}
