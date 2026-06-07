/**
 * jema-ai / saju-api — POST /api/manseryeok/verify-lite
 * Ask-one dual verify + myeongni lite (VPS Python engine).
 */
import { NextResponse } from "next/server";
import {
  runVerifyLiteEngine,
  type VerifyLiteBody,
} from "@/lib/manseryeok-verify-lite-engine";

function unauthorized(): NextResponse {
  return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
}

function isInt(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function looksLikeIsoInstant(s: string): boolean {
  const t = s.trim();
  if (t.length < 10) return false;
  if (!/^\d{4}-\d{2}-\d{2}[T ]\d/.test(t)) return false;
  return (
    /(?:\.\d+)?[zZ]$/.test(t) ||
    /[+-]\d{2}:\d{2}$/.test(t) ||
    /[+-]\d{4}$/.test(t)
  );
}

function validateBody(body: VerifyLiteBody): string[] {
  const errors: string[] = [];
  const utcMode =
    typeof body.birth_instant_utc === "string" && body.birth_instant_utc.trim().length > 0;
  if (utcMode) {
    if (!looksLikeIsoInstant(body.birth_instant_utc!)) errors.push("birth_instant_utc");
  } else {
    if (!isInt(body.year)) errors.push("year");
    if (!isInt(body.month) || body.month < 1 || body.month > 12) errors.push("month");
    if (!isInt(body.day) || body.day < 1 || body.day > 31) errors.push("day");
    if (!isInt(body.hour) || body.hour < 0 || body.hour > 23) errors.push("hour");
    if (!isInt(body.minute) || body.minute < 0 || body.minute > 59) errors.push("minute");
  }
  if (typeof body.tz !== "string" || body.tz.trim().length === 0) errors.push("tz");
  return errors;
}

export async function POST(req: Request) {
  const guard =
    process.env.MANSERYEOK_VERIFY_LITE_TOKEN?.trim() ||
    process.env.MANSERYEOK_REFERENCE_TOKEN?.trim();
  if (guard) {
    const token = req.headers.get("x-api-token")?.trim();
    if (!token || token !== guard) return unauthorized();
  }

  let body: VerifyLiteBody;
  try {
    body = (await req.json()) as VerifyLiteBody;
  } catch {
    return NextResponse.json({ success: false, error: "invalid_json" }, { status: 400 });
  }

  const invalidFields = validateBody(body);
  if (invalidFields.length > 0) {
    return NextResponse.json(
      { success: false, error: "invalid_input", invalid_fields: invalidFields },
      { status: 400 },
    );
  }

  try {
    const doc = await runVerifyLiteEngine(body);
    return NextResponse.json(
      { success: true, ...doc },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    const isRoot = msg.includes("workspace_root_not_found");
    console.error("[manseryeok/verify-lite]", msg);
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
