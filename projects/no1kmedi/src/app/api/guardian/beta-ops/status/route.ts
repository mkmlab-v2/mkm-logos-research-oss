import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";

const BETA_USAGE_DIR = path.join(process.cwd(), "memory", "commercialization");
const BETA_USAGE_FILE = path.join(BETA_USAGE_DIR, "mkmlife_beta_usage.json");

function currentUtcDateKey(): string {
  return new Date().toISOString().slice(0, 10);
}

function dailyBetaCap(): number {
  const n = Number(process.env.MKMLIFE_BETA_DAILY_CAP || 3);
  if (!Number.isFinite(n) || n < 1) return 3;
  return Math.min(20, Math.floor(n));
}

function parseAllowedInviteCodes(): string[] {
  return String(process.env.MKMLIFE_BETA_INVITE_CODES || "")
    .split(",")
    .map((x) => x.trim().toUpperCase())
    .filter(Boolean);
}

async function readBetaUsage(): Promise<Record<string, number>> {
  try {
    const raw = await fs.readFile(BETA_USAGE_FILE, "utf8");
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") return parsed as Record<string, number>;
    return {};
  } catch {
    return {};
  }
}

async function writeBetaUsage(data: Record<string, number>): Promise<void> {
  await fs.mkdir(BETA_USAGE_DIR, { recursive: true });
  await fs.writeFile(BETA_USAGE_FILE, JSON.stringify(data, null, 2), "utf8");
}

function extractAdminToken(request: NextRequest): string {
  const bearer = request.headers.get("authorization") || "";
  if (bearer.toLowerCase().startsWith("bearer ")) return bearer.slice(7).trim();
  return (request.nextUrl.searchParams.get("token") || "").trim();
}

export async function GET(request: NextRequest) {
  try {
    const expectedToken = String(
      process.env.MKMLIFE_BETA_ADMIN_TOKEN || process.env.NO1KMEDI_ADMIN_TOKEN || "",
    ).trim();
    if (!expectedToken) {
      return NextResponse.json(
        { success: false, error: "admin_token_not_configured" },
        { status: 503, headers: { "Cache-Control": "no-store" } },
      );
    }
    const provided = extractAdminToken(request);
    if (!provided || provided !== expectedToken) {
      return NextResponse.json(
        { success: false, error: "unauthorized" },
        { status: 401, headers: { "Cache-Control": "no-store" } },
      );
    }

    const dayKey = currentUtcDateKey();
    const usage = await readBetaUsage();
    const rows = Object.entries(usage)
      .filter(([k]) => k.startsWith(`${dayKey}::`))
      .map(([k, count]) => ({
        identity: k.slice(`${dayKey}::`.length),
        count: Number(count) || 0,
      }))
      .sort((a, b) => b.count - a.count);

    const totalUsed = rows.reduce((acc, row) => acc + row.count, 0);
    const capPerIdentity = dailyBetaCap();
    const inviteCodes = parseAllowedInviteCodes();

    return NextResponse.json(
      {
        success: true,
        date_utc: dayKey,
        beta_mode_enabled: String(process.env.MKMLIFE_ONEQUESTION_BETA_MODE || "") === "1",
        cap_per_identity_daily: capPerIdentity,
        invite_code_count: inviteCodes.length,
        usage: {
          identities: rows.length,
          total_used: totalUsed,
          top: rows.slice(0, 20),
        },
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json(
      { success: false, error: `beta_status_failed:${message}` },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const expectedToken = String(
      process.env.MKMLIFE_BETA_ADMIN_TOKEN || process.env.NO1KMEDI_ADMIN_TOKEN || "",
    ).trim();
    if (!expectedToken) {
      return NextResponse.json(
        { success: false, error: "admin_token_not_configured" },
        { status: 503, headers: { "Cache-Control": "no-store" } },
      );
    }
    const provided = extractAdminToken(request);
    if (!provided || provided !== expectedToken) {
      return NextResponse.json(
        { success: false, error: "unauthorized" },
        { status: 401, headers: { "Cache-Control": "no-store" } },
      );
    }

    const body = (await request.json().catch(() => ({}))) as {
      action?: string;
      identity?: string;
      date_utc?: string;
    };
    const action = String(body.action || "").trim().toLowerCase();
    if (!action) {
      return NextResponse.json(
        { success: false, error: "action_required" },
        { status: 400, headers: { "Cache-Control": "no-store" } },
      );
    }

    const usage = await readBetaUsage();
    const dayKey = String(body.date_utc || currentUtcDateKey()).trim().slice(0, 10);
    let removed = 0;

    if (action === "reset_today") {
      for (const key of Object.keys(usage)) {
        if (key.startsWith(`${dayKey}::`)) {
          delete usage[key];
          removed += 1;
        }
      }
    } else if (action === "reset_identity") {
      const identity = String(body.identity || "").trim();
      if (!identity) {
        return NextResponse.json(
          { success: false, error: "identity_required_for_reset_identity" },
          { status: 400, headers: { "Cache-Control": "no-store" } },
        );
      }
      const targetKey = `${dayKey}::${identity}`;
      if (Object.prototype.hasOwnProperty.call(usage, targetKey)) {
        delete usage[targetKey];
        removed = 1;
      }
    } else {
      return NextResponse.json(
        { success: false, error: "unsupported_action" },
        { status: 400, headers: { "Cache-Control": "no-store" } },
      );
    }

    await writeBetaUsage(usage);
    return NextResponse.json(
      {
        success: true,
        action,
        date_utc: dayKey,
        removed,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json(
      { success: false, error: `beta_reset_failed:${message}` },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}

