import { NextRequest, NextResponse } from "next/server";
import { getPayments, savePayments } from "../_store";

export const runtime = "nodejs";

function normalizeState(rawState: string | undefined): "paid" | "failed" | "pending" {
  const v = (rawState || "").toLowerCase();
  if (["paid", "success", "done", "completed", "결제완료"].includes(v)) return "paid";
  if (["failed", "cancel", "error", "취소", "실패"].includes(v)) return "failed";
  return "pending";
}

async function upsertFeedback(payload: Record<string, any>) {
  const orderId = payload.order_id || payload.ordr_idxx || payload.orderId;
  if (!orderId) return false;

  const state = normalizeState(payload.state || payload.status || payload.pay_status);
  const now = new Date().toISOString();
  const rows = await getPayments();
  const idx = rows.findIndex((x) => x.order_id === orderId);
  if (idx >= 0) {
    rows[idx] = {
      ...rows[idx],
      state,
      payapp_tid: payload.tid || payload.tr_no || rows[idx].payapp_tid,
      raw: payload,
      updated_at: now,
    };
  } else {
    rows.unshift({
      order_id: orderId,
      email: payload.email || "unknown",
      plan_code: payload.plan_code || "unknown",
      state,
      payapp_tid: payload.tid || payload.tr_no,
      raw: payload,
      created_at: now,
      updated_at: now,
    });
  }
  await savePayments(rows);
  return true;
}

export async function POST(request: NextRequest) {
  try {
    const payload = await request.json().catch(() => ({}));
    const ok = await upsertFeedback(payload);
    if (!ok) {
      return NextResponse.json({ success: false, error: "order_id missing" }, { status: 400 });
    }
    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "feedback handling failed" },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const params = request.nextUrl.searchParams;
    const payload: Record<string, any> = {};
    params.forEach((v, k) => (payload[k] = v));
    const ok = await upsertFeedback(payload);
    if (!ok) {
      return NextResponse.json({ success: false, error: "order_id missing" }, { status: 400 });
    }
    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "feedback handling failed" },
      { status: 500 }
    );
  }
}
