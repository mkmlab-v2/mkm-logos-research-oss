"use client";

import { useEffect, useState } from "react";

type KpiResponse = {
  success: boolean;
  feedback_line_count?: number;
  summary?: {
    kpi_headline?: {
      physician_approval_rate?: number | null;
      signoff_events?: number;
      conflict_reviews?: number;
      unique_encounters?: number;
      graph_build_events?: number;
      median_review_ms?: number | null;
    };
    note?: string;
  };
};

export function ClinicianGraphPilotKpiStrip() {
  const [data, setData] = useState<KpiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/clinician/graph/pilot-kpi-summary", { cache: "no-store" });
        const json = (await res.json()) as KpiResponse;
        if (!cancelled) setData(json);
      } catch {
        if (!cancelled) setError("pilot_kpi_load_failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const headline = data?.summary?.kpi_headline;

  return (
    <div className="notice-box consult-pilot-kpi-strip">
      <strong>파일럿 KPI (내부 · Track B)</strong>
      {error ? <p className="workspace-error-text">{error}</p> : null}
      {headline ? (
        <ul>
          <li>원장 승인률(up 비율): {headline.physician_approval_rate ?? "—"}</li>
          <li>sign-off 이벤트: {headline.signoff_events ?? 0}</li>
          <li>상충 검토: {headline.conflict_reviews ?? 0}</li>
          <li>고유 encounter: {headline.unique_encounters ?? 0}</li>
          <li>그래프 빌드(telemetry): {headline.graph_build_events ?? 0}</li>
          <li>검토 중앙값(ms): {headline.median_review_ms ?? "—"}</li>
          <li>피드백 로그 줄 수: {data?.feedback_line_count ?? 0}</li>
        </ul>
      ) : (
        <p className="workspace-muted">KPI 집계 데이터가 아직 없습니다.</p>
      )}
      <p className="workspace-muted">
        갱신: <code>py scripts/build_clinician_graph_pilot_kpi_report_v1.py</code>
      </p>
    </div>
  );
}
