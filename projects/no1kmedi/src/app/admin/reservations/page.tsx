"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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

type ClinicIntakeRow = {
  survey_id: string;
  submitted_at_utc: string;
  triage_level: "routine" | "priority" | "emergency";
  patient_name: string;
  patient_phone: string;
  symptom: string;
  severity_nrs: number;
  constitution_heat_cold: string;
  constitution_fatigue_recovery: string;
  kakao_summary: Record<string, unknown> | null;
};

type ClinicIntakeListResponse = {
  success: boolean;
  error?: string;
  count?: number;
  rows?: ClinicIntakeRow[];
};

const STATUS_OPTIONS: ReservationRow["status"][] = ["requested", "contacted", "booked", "closed"];

export default function AdminReservationsPage() {
  const [adminToken, setAdminToken] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [rows, setRows] = useState<ReservationRow[]>([]);
  const [clinicRows, setClinicRows] = useState<ClinicIntakeRow[]>([]);
  const [clinicTriageFilter, setClinicTriageFilter] = useState<"all" | "emergency" | "priority" | "routine">("priority");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [autoRefreshSec, setAutoRefreshSec] = useState(30);
  const [notifyEnabled, setNotifyEnabled] = useState(false);
  const [notifyPermission, setNotifyPermission] = useState<NotificationPermission>("default");
  const [seenClinicSurveyIds, setSeenClinicSurveyIds] = useState<Set<string>>(new Set());
  const [highlightedSurveyId, setHighlightedSurveyId] = useState<string>("");
  const [isLocalHost, setIsLocalHost] = useState(true);

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

  const clinicIntakeSummary = useMemo(() => {
    const total = clinicRows.length;
    const emergency = clinicRows.filter((row) => row.triage_level === "emergency").length;
    const priority = clinicRows.filter((row) => row.triage_level === "priority").length;
    const routine = clinicRows.filter((row) => row.triage_level === "routine").length;
    return { total, emergency, priority, routine };
  }, [clinicRows]);

  const sortedClinicRows = useMemo(() => {
    const rank = { priority: 0, routine: 1, emergency: 2 } as const;
    const filtered = clinicRows.filter((row) => (clinicTriageFilter === "all" ? true : row.triage_level === clinicTriageFilter));
    return [...filtered].sort((a, b) => {
      const levelDiff = rank[a.triage_level] - rank[b.triage_level];
      if (levelDiff !== 0) return levelDiff;
      return new Date(b.submitted_at_utc).getTime() - new Date(a.submitted_at_utc).getTime();
    });
  }, [clinicRows, clinicTriageFilter]);

  async function requestNotificationPermission() {
    if (!("Notification" in window)) {
      setError("이 브라우저는 데스크탑 알림을 지원하지 않습니다.");
      return;
    }
    const permission = await window.Notification.requestPermission();
    setNotifyPermission(permission);
    if (permission === "granted") {
      setNotifyEnabled(true);
      setNote("브라우저 알림이 활성화되었습니다.");
    } else {
      setNotifyEnabled(false);
      setError("알림 권한이 허용되지 않았습니다.");
    }
  }

  function focusClinicSurveyCard(surveyId: string) {
    if (!surveyId) return;
    setClinicTriageFilter("all");
    setHighlightedSurveyId(surveyId);
    window.setTimeout(() => {
      const el = document.getElementById(`clinic-survey-${surveyId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 120);
    window.setTimeout(() => setHighlightedSurveyId(""), 3500);
  }

  const loadRows = useCallback(async () => {
    const tokenRequired = !isLocalHost;
    if (tokenRequired && !adminToken.trim()) {
      setError("운영 환경에서는 관리자 토큰 입력 후 조회할 수 있습니다.");
      setNote("");
      return;
    }

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

      const clinicRes = await fetch("/api/intake/clinic-intake-v1", {
        headers: adminToken ? { "x-no1kmedi-admin-token": adminToken } : {},
      });
      const clinicJson = (await clinicRes.json()) as ClinicIntakeListResponse;
      if (clinicRes.ok && clinicJson.success) {
        const nextRows = clinicJson.rows || [];
        setClinicRows(nextRows);
        if (notifyEnabled && notifyPermission === "granted") {
          const nextIds = new Set(nextRows.map((row) => row.survey_id));
          const newImportant = nextRows.filter(
            (row) => !seenClinicSurveyIds.has(row.survey_id) && (row.triage_level === "priority" || row.triage_level === "emergency"),
          );
          newImportant.forEach((row) => {
            const title = row.triage_level === "emergency" ? "응급 접수 도착" : "우선 접수 도착";
            const body = `${row.patient_name} · ${row.symptom} · 강도 ${row.severity_nrs}`;
            const n = new window.Notification(title, { body, tag: row.survey_id });
            n.onclick = () => {
              window.focus();
              focusClinicSurveyCard(row.survey_id);
            };
          });
          setSeenClinicSurveyIds(nextIds);
        } else {
          setSeenClinicSurveyIds(new Set(nextRows.map((row) => row.survey_id)));
        }
      }
    } catch {
      setError("네트워크 오류로 예약 목록 조회에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }, [adminToken, isLocalHost, statusFilter]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      setIsLocalHost(host === "localhost" || host === "127.0.0.1");
    }
  }, []);

  useEffect(() => {
    if ("Notification" in window) {
      setNotifyPermission(window.Notification.permission);
      if (window.Notification.permission === "granted") {
        setNotifyEnabled(true);
      }
    }
  }, []);

  useEffect(() => {
    if (!autoRefreshEnabled) return;
    if (autoRefreshSec < 10) return;

    const timer = window.setInterval(() => {
      void loadRows();
    }, autoRefreshSec * 1000);

    return () => window.clearInterval(timer);
  }, [autoRefreshEnabled, autoRefreshSec, loadRows]);

  async function updateStatus(row: ReservationRow, nextStatus: ReservationRow["status"]) {
    const tokenRequired = !isLocalHost;
    if (tokenRequired && !adminToken.trim()) {
      setError("운영 환경에서는 관리자 토큰 입력 후 상태를 변경할 수 있습니다.");
      setNote("");
      return;
    }

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
        <h1 id="admin-reservation-title" className="admin-title">예약 요청 운영 대시보드</h1>
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
          <label>
            자동 새로고침
            <div className="admin-status-actions">
              <button
                type="button"
                className={`btn btn-sm ${autoRefreshEnabled ? "btn-soft" : "btn-ghost"}`}
                onClick={() => setAutoRefreshEnabled((prev) => !prev)}
              >
                {autoRefreshEnabled ? `ON (${autoRefreshSec}s)` : "OFF"}
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAutoRefreshSec(30)} disabled={!autoRefreshEnabled}>
                30s
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAutoRefreshSec(60)} disabled={!autoRefreshEnabled}>
                60s
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAutoRefreshSec(120)} disabled={!autoRefreshEnabled}>
                120s
              </button>
            </div>
          </label>
          <label>
            신규 접수 알림
            <div className="admin-status-actions">
              <button
                type="button"
                className={`btn btn-sm ${notifyEnabled ? "btn-soft" : "btn-ghost"}`}
                onClick={() => {
                  if (notifyEnabled) {
                    setNotifyEnabled(false);
                    return;
                  }
                  void requestNotificationPermission();
                }}
              >
                {notifyEnabled ? "ON (priority/emergency)" : "OFF"}
              </button>
            </div>
          </label>
        </div>
        <p className="section-lead">
          알림 권한 상태:
          {" "}
          <span className={`admin-status-pill admin-status-pill--${notifyPermission}`}>{notifyPermission}</span>
        </p>

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
                    className={`btn btn-ghost btn-sm ${row.status === status ? "is-active" : ""}`}
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

        <section className="admin-list" aria-label="clinic-intake-v1 list">
          <h2 className="admin-section-title">Clinic Intake v1 접수 목록</h2>
          {clinicIntakeSummary.emergency >= 2 ? (
            <div className="triage-emergency-banner" role="alert" aria-live="assertive">
              응급 대기 접수 {clinicIntakeSummary.emergency}건: 우선 확인이 필요합니다.
            </div>
          ) : null}
          <div className="admin-status-actions">
            <button
              type="button"
              className={`btn btn-ghost btn-sm ${clinicTriageFilter === "all" ? "is-active" : ""}`}
              onClick={() => setClinicTriageFilter("all")}
            >
              전체
            </button>
            <button
              type="button"
              className={`btn btn-ghost btn-sm ${clinicTriageFilter === "emergency" ? "is-active" : ""}`}
              onClick={() => setClinicTriageFilter("emergency")}
            >
              응급
            </button>
            <button
              type="button"
              className={`btn btn-ghost btn-sm ${clinicTriageFilter === "priority" ? "is-active" : ""}`}
              onClick={() => setClinicTriageFilter("priority")}
            >
              우선
            </button>
            <button
              type="button"
              className={`btn btn-ghost btn-sm ${clinicTriageFilter === "routine" ? "is-active" : ""}`}
              onClick={() => setClinicTriageFilter("routine")}
            >
              일반
            </button>
          </div>
          <div className="admin-summary-grid">
            <article className="admin-summary-card">
              <p>전체 접수</p>
              <strong>{clinicIntakeSummary.total}건</strong>
            </article>
            <article className="admin-summary-card">
              <p>응급(emergency)</p>
              <strong>{clinicIntakeSummary.emergency}건</strong>
            </article>
            <article className="admin-summary-card">
              <p>우선(priority)</p>
              <strong>{clinicIntakeSummary.priority}건</strong>
            </article>
            <article className="admin-summary-card">
              <p>일반(routine)</p>
              <strong>{clinicIntakeSummary.routine}건</strong>
            </article>
          </div>
          {sortedClinicRows.map((row) => (
            <article
              key={row.survey_id}
              id={`clinic-survey-${row.survey_id}`}
              className={`admin-reservation-card triage-card triage-card--${row.triage_level} ${
                highlightedSurveyId === row.survey_id ? `triage-card--highlighted triage-card--highlighted-${row.triage_level}` : ""
              }`}
            >
              <strong>{row.patient_name}</strong>
              <p>
                triage:
                {" "}
                <span className={`triage-badge triage-badge--${row.triage_level}`}>{row.triage_level}</span>
              </p>
              {row.triage_level === "emergency" ? <p className="triage-alert-text">응급 의심 접수: 우선 확인 필요</p> : null}
              <p>연락처: {row.patient_phone}</p>
              <p>증상: {row.symptom}</p>
              <p>강도: {row.severity_nrs}</p>
              {(row.constitution_heat_cold || row.constitution_fatigue_recovery) ? (
                <p>
                  체질 요약:
                  {" "}
                  {row.constitution_heat_cold ? <span className="triage-mini-tag">{row.constitution_heat_cold}</span> : null}
                  {" "}
                  {row.constitution_fatigue_recovery ? (
                    <span className="triage-mini-tag">{row.constitution_fatigue_recovery}</span>
                  ) : null}
                </p>
              ) : null}
              <p>접수 시각: {new Date(row.submitted_at_utc).toLocaleString("ko-KR")}</p>
              <p>survey_id: {row.survey_id}</p>
            </article>
          ))}
          {!busy && sortedClinicRows.length === 0 ? <p className="section-lead">clinic-intake-v1 접수 데이터가 없습니다.</p> : null}
        </section>
      </section>
    </main>
  );
}
