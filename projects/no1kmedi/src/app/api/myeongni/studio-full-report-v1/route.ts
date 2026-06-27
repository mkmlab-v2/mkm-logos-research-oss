/**
 * Myeongni Studio — full report preview (B-track · human_confirm required · send_gate HOLD).
 */
import { NextResponse } from "next/server";

import { MYEONGNI_FULL_REPORT_SSOT } from "@/lib/myeongniLiteToMindmapInputV1";
import {
  renderMyeongniFullReportMarkdown,
  runMyeongniFullReportEngine,
  summarizeMyeongniFullReport,
  type VerifyLiteBody,
} from "@/lib/manseryeok-verify-lite-engine";

type StudioBody = VerifyLiteBody & {
  include_markdown?: boolean;
};

function isInt(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function validateBody(body: StudioBody): string[] {
  const errors: string[] = [];
  if (!isInt(body.year)) errors.push("year");
  if (!isInt(body.month) || body.month! < 1 || body.month! > 12) errors.push("month");
  if (!isInt(body.day) || body.day! < 1 || body.day! > 31) errors.push("day");
  if (!isInt(body.hour) || body.hour! < 0 || body.hour! > 23) errors.push("hour");
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

  try {
    const report = await runMyeongniFullReportEngine(body);
    const summary = summarizeMyeongniFullReport(report);
    const markdown_preview = body.include_markdown
      ? await renderMyeongniFullReportMarkdown(report)
      : undefined;
    return NextResponse.json(
      {
        success: true,
        send_gate: "HOLD",
        research_only: true,
        non_gating: true,
        summary,
        markdown_preview,
        full_report_pointer: MYEONGNI_FULL_REPORT_SSOT,
        human_confirm_required: true,
        disclaimer_ko:
          "풀 리포트는 참고·교육용입니다. 임상 확정·처방은 한의사 human_confirm 경로만 사용하세요.",
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    const isRoot = msg.includes("workspace_root_not_found");
    return NextResponse.json(
      {
        success: false,
        error: isRoot ? "workspace_root_not_found" : "full_report_runtime_error",
        message: msg.slice(0, 400),
      },
      { status: isRoot ? 503 : 500 },
    );
  }
}
