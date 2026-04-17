"use client";

import { useMemo, useState } from "react";

type ReservationRow = {
  reservation_request_id: string;
  requested_at_utc: string;
  updated_at_utc: string;
  status: "requested" | "contacted" | "booked" | "closed";
  survey_id: string;
  clinic_id: string;
  clinic_name: string;
  patient_name: string;
  patient_phone: string;
};

type ReservationListResponse = {
  success: boolean;
  error?: string;
  count?: number;
  rows?: ReservationRow[];
};

type ReservationPatchResponse = {
  success: boolean;
  error?: string;
  row?: ReservationRow;
};

const STATUS_OPTIONS: ReservationRow["status"][] = ["requested", "contacted", "booked", "closed"];

export default function AdminReservationsPage() {
  const [adminToken, setAdminToken] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [rows, setRows] = useState<ReservationRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const summary = useMemo(() => {
    const total = rows.length;
    const booked = rows.filter((row) => row.status === "booked").length;
    const contacted = rows.filter((row) => row.status === "contacted").length;
    const closed = rows.filter((row) => row.status === "closed").length;
    const bookedRate = total > 0 ? Math.round((booked / total) * 100) : 0;
    const byClinic = rows.reduce<Record<string, { total: number; booked: number }>>((acc, row) => {
      if (!acc[row.clinic_name]) acc[row.clinic_name] = { total: 0, booked: 0 };
      acc[row.clinic_name].total += 1;
      if (row.status === "booked") acc[row.clinic_name].booked += 1;
      return acc;
    }, {});
    const clinicCards = Object.entries(byClinic).map(([clinicName, stats]) => ({
      clinicName,
      total: stats.total,
      bookedRate: Math.round((stats.booked / stats.total) * 100),
    }));
    return { total, booked, contacted, closed, bookedRate, clinicCards };
  }, [rows]);

  async function loadRows() {
    setBusy(true);
    setError("");
    setNote("");
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      const url = `/api/intake/reservations${params.size > 0 ? `?${params.toString()}` : ""}`;
      const res = await fetch(url, {
        headers: adminToken ? { "x-no1kmedi-admin-token": adminToken } : {},
      });
      const json = (await res.json()) as ReservationListResponse;
      if (!res.ok || !json.success) {
        setError(json.error || "예약 목록을 불러오지 못했습니다.");
        return;
      }
      setRows(json.rows || []);
      setNote(`예약 요청 ${json.count || 0}건을 조회했습니다.`);
    } catch {
      setError("네트워크 오류로 예약 목록 조회에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(row: ReservationRow, nextStatus: ReservationRow["status"]) {
    setError("");
    setNote("");
    try {
      const res = await fetch("/api/intake/reservations", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(adminToken ? { "x-no1kmedi-admin-token": adminToken } : {}),
        },
        body: JSON.stringify({
          reservation_request_id: row.reservation_request_id,
          status: nextStatus,
        }),
      });
      const json = (await res.json()) as ReservationPatchResponse;
      if (!res.ok || !json.success || !json.row) {
        setError(json.error || "상태 변경에 실패했습니다.");
        return;
      }
      setRows((prev) => prev.map((item) => (item.reservation_request_id === json.row!.reservation_request_id ? json.row! : item)));
      setNote(`상태를 ${nextStatus}로 변경했습니다.`);
    } catch {
      setError("네트워크 오류로 상태 변경에 실패했습니다.");
    }
  }

  return (
    <main className="admin-page">
      <section className="admin-panel" aria-labelledby="admin-reservation-title">
        <h1 id="admin-reservation-title">예약 요청 운영 대시보드</h1>
        <p className="section-lead">제휴 한의원 예약 요청을 조회하고 상태를 변경합니다.</p>

        <div className="admin-controls">
          <label>
            관리자 토큰
            <input
              type="password"
              value={adminToken}
              onChange={(e) => setAdminToken(e.target.value)}
              placeholder="NO1KMEDI_ADMIN_TOKEN"
            />
          </label>
          <label>
            상태 필터
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">전체</option>
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={loadRows}>
            {busy ? "조회 중..." : "예약 목록 조회"}
          </button>
        </div>

        {note ? <p className="lead-success">{note}</p> : null}
        {error ? <p className="consult-error">{error}</p> : null}

        <div className="admin-summary-grid">
          <article className="admin-summary-card">
            <p>전체 요청</p>
            <strong>{summary.total}건</strong>
          </article>
          <article className="admin-summary-card">
            <p>예약 완료(booked)</p>
            <strong>{summary.booked}건</strong>
          </article>
          <article className="admin-summary-card">
            <p>연락 진행(contacted)</p>
            <strong>{summary.contacted}건</strong>
          </article>
          <article className="admin-summary-card">
            <p>완료율</p>
            <strong>{summary.bookedRate}%</strong>
          </article>
        </div>

        {summary.clinicCards.length > 0 ? (
          <div className="admin-summary-grid">
            {summary.clinicCards.map((clinic) => (
              <article key={clinic.clinicName} className="admin-summary-card">
                <p>{clinic.clinicName}</p>
                <strong>
                  {clinic.total}건 · 완료율 {clinic.bookedRate}%
                </strong>
              </article>
            ))}
          </div>
        ) : null}

        <div className="admin-list">
          {rows.map((row) => (
            <article key={row.reservation_request_id} className="admin-reservation-card">
              <strong>{row.clinic_name}</strong>
              <p>환자: {row.patient_name}</p>
              <p>연락처: {row.patient_phone}</p>
              <p>현재 상태: {row.status}</p>
              <p>요청 ID: {row.reservation_request_id}</p>
              <p>요청 시각: {new Date(row.requested_at_utc).toLocaleString("ko-KR")}</p>
              <div className="admin-status-actions">
                {STATUS_OPTIONS.map((status) => (
                  <button
                    key={status}
                    type="button"
                    className={`btn btn-ghost ${row.status === status ? "is-active" : ""}`}
                    onClick={() => updateStatus(row, status)}
                    disabled={row.status === status}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </article>
          ))}
          {!busy && rows.length === 0 ? <p className="section-lead">조회된 예약 요청이 없습니다.</p> : null}
        </div>
      </section>
    </main>
  );
}
