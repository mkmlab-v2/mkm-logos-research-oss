import { NextRequest, NextResponse } from "next/server";
import { getVerifications, saveVerifications } from "../../../payment/payapp/_store";

export const runtime = "nodejs";

const REVIEW_RATE_LIMIT_MAX = Number(process.env.NO1KMEDI_REVIEW_RATE_LIMIT_MAX || 20);
const REVIEW_RATE_LIMIT_WINDOW_MS = Number(process.env.NO1KMEDI_REVIEW_RATE_LIMIT_WINDOW_MS || 60_000);
const reviewRateWindow = new Map<string, { count: number; resetAt: number }>();

function readClientIp(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) return forwarded.split(",")[0].trim();
  const realIp = request.headers.get("x-real-ip");
  if (realIp) return realIp.trim();
  return "unknown";
}

function checkRateLimit(key: string): { allowed: boolean; retryAfterSeconds: number } {
  const now = Date.now();
  const entry = reviewRateWindow.get(key);
  if (!entry || now > entry.resetAt) {
    reviewRateWindow.set(key, { count: 1, resetAt: now + REVIEW_RATE_LIMIT_WINDOW_MS });
    return { allowed: true, retryAfterSeconds: 0 };
  }

  if (entry.count >= REVIEW_RATE_LIMIT_MAX) {
    return { allowed: false, retryAfterSeconds: Math.max(1, Math.ceil((entry.resetAt - now) / 1000)) };
  }

  entry.count += 1;
  reviewRateWindow.set(key, entry);
  return { allowed: true, retryAfterSeconds: 0 };
}

export async function POST(request: NextRequest) {
  try {
    const limiter = checkRateLimit(readClientIp(request));
    if (!limiter.allowed) {
      return NextResponse.json(
        {
          success: false,
          error: "rate_limited",
          retry_after_seconds: limiter.retryAfterSeconds,
        },
        {
          status: 429,
          headers: { "Retry-After": String(limiter.retryAfterSeconds) },
        },
      );
    }

    const body = await request.json();
    const { verification_id, decision, admin_token, reviewer } = body ?? {};
    if (!verification_id || !decision) {
      return NextResponse.json(
        { success: false, error: "verification_id and decision are required." },
        { status: 400 }
      );
    }

    const expected = process.env.NO1KMEDI_ADMIN_TOKEN;
    const headerToken =
      request.headers.get("x-no1kmedi-admin-token") ||
      request.headers.get("authorization")?.replace(/^Bearer\s+/i, "").trim() ||
      "";
    const providedToken = headerToken || admin_token || "";

    if (expected && providedToken !== expected) {
      return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
    }

    if (!["approved", "rejected"].includes(decision)) {
      return NextResponse.json({ success: false, error: "decision must be approved or rejected" }, { status: 400 });
    }

    const rows = await getVerifications();
    const idx = rows.findIndex((x) => x.id === verification_id);
    if (idx < 0) {
      return NextResponse.json({ success: false, error: "verification not found" }, { status: 404 });
    }

    rows[idx] = {
      ...rows[idx],
      status: decision,
      reviewed_by: reviewer || "admin",
      updated_at: new Date().toISOString(),
    };
    await saveVerifications(rows);

    return NextResponse.json({
      success: true,
      verification_id,
      verification_status: rows[idx].status,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "verification review failed" },
      { status: 500 }
    );
  }
}
