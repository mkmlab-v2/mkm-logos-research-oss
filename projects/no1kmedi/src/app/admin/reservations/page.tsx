"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  KM_CDS_UI_ANALYTICS_EVENTS_V1,
  trackKmCdsUiEvent,
} from "@/lib/km-cds-ui-analytics-events-v1";

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

type TelemetrySummaryResponse = {
  success: boolean;
  error?: string;
  lookback_days?: number;
  kpi?: {
    public_workspace_mount: number;
    public_mode_ack: number;
    public_mode_decline: number;
    public_ack_rate: number;
    admin_alert_click_consumer: number;
    admin_alert_click_safety: number;
    admin_alert_days_7d: number;
    admin_alert_clicks_total: number;
    admin_alert_click_rate_per_alert_day: number;
    admin_reco_click_consumer: number;
    admin_reco_click_safety: number;
    admin_reco_clicks_total: number;
    admin_reco_click_rate_per_alert_day: number;
    admin_checklist_toggle_total: number;
    admin_priority_action_show_total: number;
    admin_priority_action_click_total: number;
    admin_priority_action_exec_rate: number;
  };
  trend_7d?: Array<{
    day: string;
    mount: number;
    ack: number;
    decline: number;
    admin_click_consumer: number;
    admin_click_safety: number;
    admin_reco_click_consumer: number;
    admin_reco_click_safety: number;
    ack_rate: number;
  }>;
};

const STATUS_OPTIONS: ReservationRow["status"][] = ["requested", "contacted", "booked", "closed"];

function ackRateBand(rate: number): "ok" | "watch" | "hold" {
  if (rate >= 0.8) return "ok";
  if (rate >= 0.6) return "watch";
  return "hold";
}

function completionBand(rate: number): "ok" | "watch" | "hold" {
  if (rate >= 0.8) return "ok";
  if (rate >= 0.5) return "watch";
  return "hold";
}

function priorityExecBand(kpi: NonNullable<TelemetrySummaryResponse["kpi"]>): "ok" | "watch" | "hold" {
  if (kpi.admin_alert_days_7d <= 0) return "ok";
  if (kpi.admin_priority_action_show_total <= 0) return "hold";
  if (kpi.admin_priority_action_exec_rate >= 0.7) return "ok";
  if (kpi.admin_priority_action_exec_rate >= 0.3) return "watch";
  return "hold";
}

function worstBand(bands: Array<"ok" | "watch" | "hold">): "ok" | "watch" | "hold" {
  if (bands.includes("hold")) return "hold";
  if (bands.includes("watch")) return "watch";
  return "ok";
}

function bandPriority(band: "ok" | "watch" | "hold"): number {
  if (band === "hold") return 0;
  if (band === "watch") return 1;
  return 2;
}

function alertResponseStatus(kpi: NonNullable<TelemetrySummaryResponse["kpi"]>): {
  tone: "ok" | "watch" | "hold";
  text: string;
} {
  if (kpi.admin_alert_days_7d <= 0) {
    return { tone: "ok", text: "최근 7일 경고일이 없습니다." };
  }
  if (kpi.admin_alert_clicks_total <= 0) {
    return { tone: "hold", text: "경고일은 있으나 운영 클릭 반응이 없습니다. 즉시 점검 필요." };
  }
  if (kpi.admin_alert_click_rate_per_alert_day < 1) {
    return { tone: "watch", text: "경고일 대비 운영 반응이 낮습니다. 모달/문구/동선 확인 권장." };
  }
  return { tone: "ok", text: "경고일 대비 운영 반응이 확보되었습니다." };
}

function alertRecommendedAction(kpi: NonNullable<TelemetrySummaryResponse["kpi"]>): {
  label: string;
  href: string;
  event: "ADMIN_KPI_RECO_CLICK_CONSUMER_V1" | "ADMIN_KPI_RECO_CLICK_SAFETY_V1";
} {
  const status = alertResponseStatus(kpi);
  if (status.tone === "hold") {
    return {
      label: "권장: 안전·고지 패널 우선 점검",
      href: "/consumer?panel=safety",
      event: "ADMIN_KPI_RECO_CLICK_SAFETY_V1",
    };
  }
  return {
    label: "권장: 일반인 워크스페이스 점검",
    href: "/consumer",
    event: "ADMIN_KPI_RECO_CLICK_CONSUMER_V1",
  };
}

function telemetryInterpretationTag(kpi: NonNullable<TelemetrySummaryResponse["kpi"]>): {
  tone: "ok" | "watch" | "hold";
  label: string;
  detail: string;
} {
  const alertRate = kpi.admin_alert_click_rate_per_alert_day;
  const recoRate = kpi.admin_reco_click_rate_per_alert_day;
  if (kpi.admin_alert_days_7d <= 0) {
    return { tone: "ok", label: "STABLE", detail: "경고일이 없어 운영 개입 신호가 낮습니다." };
  }
  if (alertRate >= 1 && recoRate < 0.5) {
    return { tone: "watch", label: "CTA_LOW", detail: "배너 반응은 있으나 권장 액션 전환이 낮습니다." };
  }
  if (alertRate > 0 && recoRate === 0) {
    return { tone: "hold", label: "ACTION_GAP", detail: "배너 클릭 후 권장 액션으로 이어지지 않습니다." };
  }
  if (alertRate < 0.5 && recoRate < 0.5) {
    return { tone: "hold", label: "LOW_RESPONSE", detail: "배너/권장 액션 모두 반응이 낮습니다." };
  }
  return { tone: "ok", label: "ALIGNED", detail: "배너와 권장 액션 반응이 함께 확보됩니다." };
}

function telemetryChecklist(label: string): string[] {
  if (label === "LOW_RESPONSE") {
    return [
      "일반인 모드 진입 전 안내 문구를 1문장으로 단순화합니다.",
      "동의 버튼/권장 액션 버튼 위치를 첫 화면 가시 영역으로 올립니다.",
      "24시간 후 동의율·클릭률 재점검 후 문구 A/B를 시작합니다.",
    ];
  }
  if (label === "ACTION_GAP") {
    return [
      "배너 버튼 라벨을 문제-행동형 문구로 교체합니다.",
      "권장 액션 클릭 후 랜딩 화면 로딩 지연 여부를 점검합니다.",
      "운영자에게 권장 액션 목적(무엇을 확인하는지) 한 줄 툴팁을 추가합니다.",
    ];
  }
  if (label === "CTA_LOW") {
    return [
      "배너 문구는 유지하고 CTA 카피만 실험군 1개를 추가합니다.",
      "권장 액션 버튼을 카드 상단으로 1단계 올려 노출합니다.",
      "3일 단위로 클릭/경고일 비율 변화를 추적합니다.",
    ];
  }
  if (label === "STABLE") {
    return [
      "현재 문구/동선을 잠금하고 주간 점검만 수행합니다.",
      "임계치 하향(60%) 발생 시 즉시 경고 흐름을 재개합니다.",
      "운영 로그 누락 여부만 점검합니다.",
    ];
  }
  return [
    "현재 조합을 유지하고 주간 리포트로 추세만 확인합니다.",
    "경고일 재발 시 안전·고지 패널 점검을 우선 실행합니다.",
    "월간 기준으로 문구 번들 버전만 관리합니다.",
  ];
}

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
  const [telemetryKpi, setTelemetryKpi] = useState<TelemetrySummaryResponse["kpi"] | null>(null);
  const [telemetryLookbackDays, setTelemetryLookbackDays] = useState<number>(7);
  const [telemetryTrend, setTelemetryTrend] = useState<NonNullable<TelemetrySummaryResponse["trend_7d"]>>([]);
  const [checklistChecked, setChecklistChecked] = useState<Record<string, boolean>>({});
  const telemetryTrendMinMax = useMemo(() => {
    if (!telemetryTrend.length) return null;
    const rates = telemetryTrend.map((d) => d.ack_rate);
    return {
      min: Math.min(...rates),
      max: Math.max(...rates),
    };
  }, [telemetryTrend]);
  const telemetryResponseStatus = useMemo(
    () => (telemetryKpi ? alertResponseStatus(telemetryKpi) : null),
    [telemetryKpi],
  );
  const telemetryRecommendedAction = useMemo(
    () => (telemetryKpi ? alertRecommendedAction(telemetryKpi) : null),
    [telemetryKpi],
  );
  const telemetryInterpretation = useMemo(
    () => (telemetryKpi ? telemetryInterpretationTag(telemetryKpi) : null),
    [telemetryKpi],
  );
  const telemetryChecklistItems = useMemo(
    () => (telemetryInterpretation ? telemetryChecklist(telemetryInterpretation.label) : []),
    [telemetryInterpretation],
  );
  const checklistStorageKey = useMemo(
    () => `mkm_admin_kpi_checklist_state_v1_${telemetryInterpretation?.label || "none"}`,
    [telemetryInterpretation],
  );
  const checklistCompletion = useMemo(() => {
    const total = telemetryChecklistItems.length;
    if (total <= 0) return { completed: 0, total: 0, rate: 0 };
    let completed = 0;
    telemetryChecklistItems.forEach((item, idx) => {
      const key = `${idx}:${item}`;
      if (checklistChecked[key]) completed += 1;
    });
    return { completed, total, rate: completed / total };
  }, [telemetryChecklistItems, checklistChecked]);
  const overallOpsBand = useMemo(() => {
    if (!telemetryKpi) return null;
    const ackBand = ackRateBand(telemetryKpi.public_ack_rate);
    const alertBand = telemetryResponseStatus?.tone || "watch";
    const completion = checklistCompletion.total > 0 ? completionBand(checklistCompletion.rate) : "watch";
    const execution = priorityExecBand(telemetryKpi);
    return worstBand([ackBand, alertBand, completion, execution]);
  }, [telemetryKpi, telemetryResponseStatus, checklistCompletion]);
  const overallBreakdown = useMemo(() => {
    if (!telemetryKpi) return null;
    const ackBand = ackRateBand(telemetryKpi.public_ack_rate);
    const alertBand = telemetryResponseStatus?.tone || "watch";
    const completion = checklistCompletion.total > 0 ? completionBand(checklistCompletion.rate) : "watch";
    const execution = priorityExecBand(telemetryKpi);
    return { ackBand, alertBand, completion, execution };
  }, [telemetryKpi, telemetryResponseStatus, checklistCompletion]);
  const overallBreakdownSorted = useMemo(() => {
    if (!overallBreakdown) return [];
    const entries: Array<{ key: "ACK" | "ALERT" | "CHECKLIST" | "EXEC"; band: "ok" | "watch" | "hold" }> = [
      { key: "ACK", band: overallBreakdown.ackBand },
      { key: "ALERT", band: overallBreakdown.alertBand },
      { key: "CHECKLIST", band: overallBreakdown.completion },
      { key: "EXEC", band: overallBreakdown.execution },
    ];
    return entries.sort((a, b) => {
      const pa = bandPriority(a.band);
      const pb = bandPriority(b.band);
      if (pa !== pb) return pa - pb;
      return a.key.localeCompare(b.key);
    });
  }, [overallBreakdown]);
  const holdAxisCount = useMemo(
    () => overallBreakdownSorted.filter((item) => item.band === "hold").length,
    [overallBreakdownSorted],
  );

  useEffect(() => {
    if (overallOpsBand !== "hold" || !telemetryRecommendedAction) return;
    try {
      const key = `mkm_admin_kpi_priority_action_show_v1_${telemetryRecommendedAction.href}`;
      if (window.sessionStorage.getItem(key)) return;
      window.sessionStorage.setItem(key, "1");
      trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.ADMIN_KPI_PRIORITY_ACTION_SHOW_V1, {
        surface: "settings",
        locale: "ko-KR",
        copy_bundle_id: "km_admin_kpi_priority_action_v1",
      });
    } catch {
      // ignore storage failures
    }
  }, [overallOpsBand, telemetryRecommendedAction]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(checklistStorageKey);
      if (!raw) {
        setChecklistChecked({});
        return;
      }
      const parsed = JSON.parse(raw) as Record<string, boolean>;
      setChecklistChecked(parsed || {});
    } catch {
      setChecklistChecked({});
    }
  }, [checklistStorageKey]);

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
  }, [adminToken, isLocalHost, notifyEnabled, notifyPermission, seenClinicSurveyIds, statusFilter]);

  const loadTelemetryKpi = useCallback(async () => {
    try {
      const res = await fetch("/api/telemetry/summary");
      const json = (await res.json()) as TelemetrySummaryResponse;
      if (res.ok && json.success && json.kpi) {
        setTelemetryKpi(json.kpi);
        setTelemetryLookbackDays(json.lookback_days || 7);
        setTelemetryTrend(json.trend_7d || []);
      }
    } catch {
      // summary can be absent in early environments
    }
  }, []);

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
    void loadTelemetryKpi();
  }, [loadTelemetryKpi]);

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

  const toggleChecklistItem = useCallback(
    (idx: number, item: string) => {
      const key = `${idx}:${item}`;
      setChecklistChecked((prev) => {
        const next = { ...prev, [key]: !prev[key] };
        try {
          window.localStorage.setItem(checklistStorageKey, JSON.stringify(next));
        } catch {
          // ignore storage errors
        }
        return next;
      });
      const checked = !checklistChecked[key];
      trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.ADMIN_KPI_CHECKLIST_TOGGLE_V1, {
        surface: "settings",
        locale: "ko-KR",
        copy_bundle_id: "km_admin_kpi_checklist_v1",
        item_key: key,
        item_label: item,
        checked,
        interpretation_label: telemetryInterpretation?.label || "none",
      });
    },
    [checklistChecked, checklistStorageKey, telemetryInterpretation],
  );

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
        {telemetryTrendMinMax && telemetryTrendMinMax.min < 0.6 ? (
          <div className="admin-kpi-alert-banner" role="alert" aria-live="polite">
            <p>일반인 모드 동의율이 최근 7일 구간에서 60% 미만으로 내려간 날이 있습니다. 동의 문구/진입 플로우를 점검하세요.</p>
            <div className="admin-kpi-alert-actions">
              <a
                className="btn btn-ghost btn-sm"
                href="/consumer"
                target="_blank"
                rel="noreferrer"
                onClick={() =>
                  trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.ADMIN_KPI_ALERT_CLICK_CONSUMER_V1, {
                    surface: "settings",
                    locale: "ko-KR",
                    copy_bundle_id: "km_admin_kpi_alert_v1",
                  })
                }
              >
                일반인 워크스페이스 점검
              </a>
              <a
                className="btn btn-ghost btn-sm"
                href="/consumer?panel=safety"
                target="_blank"
                rel="noreferrer"
                onClick={() =>
                  trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.ADMIN_KPI_ALERT_CLICK_SAFETY_V1, {
                    surface: "settings",
                    locale: "ko-KR",
                    copy_bundle_id: "km_admin_kpi_alert_v1",
                  })
                }
              >
                안전·고지 패널 점검
              </a>
            </div>
          </div>
        ) : null}

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
          <article
            className={`admin-summary-card${
              telemetryTrendMinMax && telemetryTrendMinMax.min < 0.6 ? " admin-summary-card--kpi-alert" : ""
            }`}
          >
            <p>일반인 모드 동의율 ({telemetryLookbackDays}일)</p>
            <strong>{telemetryKpi ? `${Math.round(telemetryKpi.public_ack_rate * 100)}%` : "—"}</strong>
            {overallOpsBand ? (
              <p className={`admin-kpi-overall-line is-${overallOpsBand}`}>
                종합 상태: {overallOpsBand.toUpperCase()} (동의율/반응률/완료율/실행률 통합)
              </p>
            ) : null}
            {overallBreakdown ? (
              <p className={`admin-kpi-breakdown-line${holdAxisCount >= 2 ? " is-severe" : ""}`}>
                {overallBreakdownSorted.map((item, idx) => (
                  <span key={item.key}>
                    <span className={`admin-kpi-axis-tag is-${item.band}`}>
                      {item.key}:{item.band.toUpperCase()}
                    </span>
                    {idx < overallBreakdownSorted.length - 1 ? " · " : ""}
                  </span>
                ))}
              </p>
            ) : null}
            {overallOpsBand === "hold" && telemetryRecommendedAction ? (
              <a
                className={`btn btn-primary btn-sm admin-kpi-priority-action${
                  holdAxisCount >= 2 ? " is-severe" : ""
                }`}
                href={telemetryRecommendedAction.href}
                target="_blank"
                rel="noreferrer"
                onClick={() =>
                  trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.ADMIN_KPI_PRIORITY_ACTION_CLICK_V1, {
                    surface: "settings",
                    locale: "ko-KR",
                    copy_bundle_id: "km_admin_kpi_priority_action_v1",
                  })
                }
              >
                즉시 조치 1순위: {telemetryRecommendedAction.label}
              </a>
            ) : null}
            {telemetryKpi ? (
              <span className={`admin-kpi-pill is-${ackRateBand(telemetryKpi.public_ack_rate)}`}>
                {ackRateBand(telemetryKpi.public_ack_rate).toUpperCase()}
              </span>
            ) : null}
            {telemetryKpi ? (
              <p>
                동의 {telemetryKpi.public_mode_ack} / 진입 {telemetryKpi.public_workspace_mount} · 거절{" "}
                {telemetryKpi.public_mode_decline}
              </p>
            ) : (
              <p>요약 생성 전</p>
            )}
            {telemetryKpi ? (
              <p>
                경고 배너 클릭: 일반인 점검 {telemetryKpi.admin_alert_click_consumer} · 안전 패널{" "}
                {telemetryKpi.admin_alert_click_safety}
              </p>
            ) : null}
            {telemetryKpi ? (
              <p>
                배너 반응률(클릭/경고일): {telemetryKpi.admin_alert_clicks_total} / {telemetryKpi.admin_alert_days_7d} ={" "}
                {telemetryKpi.admin_alert_days_7d > 0
                  ? telemetryKpi.admin_alert_click_rate_per_alert_day.toFixed(2)
                  : "0.00"}
              </p>
            ) : null}
            {telemetryKpi ? (
              <p>
                권장액션 반응률(클릭/경고일): {telemetryKpi.admin_reco_clicks_total} / {telemetryKpi.admin_alert_days_7d} ={" "}
                {telemetryKpi.admin_alert_days_7d > 0
                  ? telemetryKpi.admin_reco_click_rate_per_alert_day.toFixed(2)
                  : "0.00"}
              </p>
            ) : null}
            {telemetryInterpretation ? (
              <p className={`admin-kpi-interpretation is-${telemetryInterpretation.tone}`}>
                [{telemetryInterpretation.label}] {telemetryInterpretation.detail}
              </p>
            ) : null}
            {telemetryChecklistItems.length > 0 ? (
              <ul className="admin-kpi-checklist">
                {telemetryChecklistItems.map((item, idx) => {
                  const key = `${idx}:${item}`;
                  const checked = Boolean(checklistChecked[key]);
                  return (
                    <li key={item}>
                      <label className={`admin-kpi-checklist-item${checked ? " is-checked" : ""}`}>
                        <input type="checkbox" checked={checked} onChange={() => toggleChecklistItem(idx, item)} />
                        <span>{item}</span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            ) : null}
            {checklistCompletion.total > 0 ? (
              <p>
                체크리스트 완료율: {checklistCompletion.completed}/{checklistCompletion.total} (
                {Math.round(checklistCompletion.rate * 100)}%)
                <span className={`admin-kpi-pill is-${completionBand(checklistCompletion.rate)} admin-kpi-inline-pill`}>
                  {completionBand(checklistCompletion.rate).toUpperCase()}
                </span>
              </p>
            ) : null}
            {telemetryKpi ? (
              <p className={`admin-kpi-response-note is-${telemetryResponseStatus?.tone}`}>
                {telemetryResponseStatus?.text}
              </p>
            ) : null}
            {telemetryKpi ? <p>체크 토글 로그(7일): {telemetryKpi.admin_checklist_toggle_total}</p> : null}
            {telemetryKpi ? (
              <p>
                HOLD 대응 실행률(클릭/노출): {telemetryKpi.admin_priority_action_click_total} /{" "}
                {telemetryKpi.admin_priority_action_show_total} ={" "}
                {telemetryKpi.admin_priority_action_show_total > 0
                  ? telemetryKpi.admin_priority_action_exec_rate.toFixed(2)
                  : "0.00"}
              </p>
            ) : null}
            {telemetryKpi && telemetryRecommendedAction ? (
              <a
                className="btn btn-ghost btn-sm admin-kpi-reco-action"
                href={telemetryRecommendedAction.href}
                target="_blank"
                rel="noreferrer"
                onClick={() =>
                  trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1[telemetryRecommendedAction.event], {
                    surface: "settings",
                    locale: "ko-KR",
                    copy_bundle_id: "km_admin_kpi_recommended_action_v1",
                  })
                }
              >
                {telemetryRecommendedAction.label}
              </a>
            ) : null}
            {telemetryTrend.length > 0 ? (
              <div className="admin-kpi-trend">
                {telemetryTrendMinMax ? (
                  <p className="admin-kpi-trend-minmax">
                    최근 {telemetryTrend.length}일 최저 {Math.round(telemetryTrendMinMax.min * 100)}% · 최고{" "}
                    {Math.round(telemetryTrendMinMax.max * 100)}%
                  </p>
                ) : null}
                {telemetryTrend.map((d) => (
                  <div key={d.day} className="admin-kpi-trend-row">
                    <span>{d.day.slice(5)}</span>
                    <div className="admin-kpi-trend-bar">
                      <div
                        className={`admin-kpi-trend-bar-fill is-${ackRateBand(d.ack_rate)}`}
                        style={{ width: `${Math.max(0, Math.min(100, Math.round(d.ack_rate * 100)))}%` }}
                      />
                    </div>
                    <span>{Math.round(d.ack_rate * 100)}%</span>
                  </div>
                ))}
              </div>
            ) : null}
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
