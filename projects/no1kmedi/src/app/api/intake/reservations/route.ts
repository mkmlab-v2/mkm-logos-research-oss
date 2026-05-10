import { NextRequest, NextResponse } from "next/server";
import { getReservations, saveReservations } from "@/app/api/intake/_store";
import { hasAdminTokenAccess } from "@/lib/internal-api-auth";

type ReservationStatus = "requested" | "contacted" | "booked" | "closed";

const ALLOWED: ReservationStatus[] = ["requested", "contacted", "booked", "closed"];

function isAllowedStatus(value: unknown): value is ReservationStatus {
  return typeof value === "string" && ALLOWED.includes(value as ReservationStatus);
}

export async function GET(request: NextRequest) {
  if (!hasAdminTokenAccess(request)) {
    return NextResponse.json({ success: false, error: "admin_token_required" }, { status: 401 });
  }

  const status = request.nextUrl.searchParams.get("status");
  const clinicId = request.nextUrl.searchParams.get("clinic_id");
  const all = await getReservations();
  const filtered = all.filter((row) => {
    if (status && row.status !== status) return false;
    if (clinicId && row.clinic_id !== clinicId) return false;
    return true;
  });

  return NextResponse.json({ success: true, count: filtered.length, rows: filtered }, { status: 200 });
}

export async function PATCH(request: NextRequest) {
  if (!hasAdminTokenAccess(request)) {
    return NextResponse.json({ success: false, error: "admin_token_required" }, { status: 401 });
  }

  const body = (await request.json()) as {
    reservation_request_id?: string;
    status?: ReservationStatus;
  };

  if (!body?.reservation_request_id) {
    return NextResponse.json({ success: false, error: "reservation_request_id_required" }, { status: 400 });
  }
  if (!isAllowedStatus(body.status)) {
    return NextResponse.json({ success: false, error: "invalid_status" }, { status: 400 });
  }

  const rows = await getReservations();
  const idx = rows.findIndex((r) => r.reservation_request_id === body.reservation_request_id);
  if (idx < 0) return NextResponse.json({ success: false, error: "reservation_not_found" }, { status: 404 });

  rows[idx] = { ...rows[idx], status: body.status, updated_at_utc: new Date().toISOString() };
  await saveReservations(rows);

  return NextResponse.json({ success: true, row: rows[idx] }, { status: 200 });
}
