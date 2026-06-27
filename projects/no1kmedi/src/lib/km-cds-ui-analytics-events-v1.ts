/**
 * MKM 한의 CDS / 일반인 모드 전환용 클라이언트 분석 이벤트 키 v1.
 * 서버·스크립트와 동일 문자열을 쓰려면 `scripts/km_cds_ui_analytics_events_v1.py`와 함께 유지한다.
 *
 * `PUBLIC_WORKSPACE_MOUNT_V1`: 일반인 워크스페이스 진입(퍼널)·법적 동의 아님.
 * 동의 완료는 `PUBLIC_MODE_ENTER_ACK`만 사용.
 */

import { trackClientEvent } from "./client-telemetry";

export const KM_CDS_UI_ANALYTICS_EVENTS_V1 = {
  PUBLIC_MODE_ENTER_ACK: "public_mode_enter_ack_v1",
  PUBLIC_MODE_EXIT: "public_mode_exit",
  CDS_MODE_ENTER: "cds_mode_enter",
  PUBLIC_MODE_ENTER_DECLINED: "public_mode_enter_declined_v1",
  CDS_MODE_EXIT: "cds_mode_exit",
  /** Funnel / 세션 진입. 면책 동의와 별개. */
  PUBLIC_WORKSPACE_MOUNT_V1: "public_workspace_mount_v1",
  /** Admin KPI alert shortcut clicks. */
  ADMIN_KPI_ALERT_CLICK_CONSUMER_V1: "admin_kpi_alert_click_consumer_v1",
  ADMIN_KPI_ALERT_CLICK_SAFETY_V1: "admin_kpi_alert_click_safety_v1",
  /** Admin recommended-action CTA clicks. */
  ADMIN_KPI_RECO_CLICK_CONSUMER_V1: "admin_kpi_reco_click_consumer_v1",
  ADMIN_KPI_RECO_CLICK_SAFETY_V1: "admin_kpi_reco_click_safety_v1",
  /** Admin checklist checkbox toggle. */
  ADMIN_KPI_CHECKLIST_TOGGLE_V1: "admin_kpi_checklist_toggle_v1",
  /** HOLD priority action exposure/click tracking. */
  ADMIN_KPI_PRIORITY_ACTION_SHOW_V1: "admin_kpi_priority_action_show_v1",
  ADMIN_KPI_PRIORITY_ACTION_CLICK_V1: "admin_kpi_priority_action_click_v1",
  /** Clinician workspace: patient_care_bundle from CDS envelope. */
  CDS_BUNDLE_GENERATE_V1: "cds_bundle_generate_v1",
  /** Clinician graph pilot KPI (Track B · internal). */
  CLINICIAN_GRAPH_BUILD_V1: "clinician_graph_build_v1",
  CLINICIAN_GRAPH_VIEW_MODE_V1: "clinician_graph_view_mode_v1",
  CLINICIAN_GRAPH_REVIEW_FEEDBACK_V1: "clinician_graph_review_feedback_v1",
  CLINICIAN_GRAPH_SIGNOFF_V1: "clinician_graph_signoff_v1",
  CLINICIAN_GRAPH_REVIEW_TIMING_V1: "clinician_graph_review_timing_v1",
} as const;

export type KmCdsUiAnalyticsEventNameV1 =
  (typeof KM_CDS_UI_ANALYTICS_EVENTS_V1)[keyof typeof KM_CDS_UI_ANALYTICS_EVENTS_V1];

/** PHI 금지. 동의 문구 번들·표면 구분용 보조 필드. */
export type KmCdsUiAnalyticsPayloadV1 = {
  surface?: "modal" | "fullscreen" | "settings" | "workspace";
  locale?: string;
  copy_bundle_id?: string;
  encounter_ref?: string;
  target_id?: string;
  feedback?: string;
  reason_code?: string;
  view_mode?: string;
  node_count?: number;
  edge_count?: number;
  conflict_group_count?: number;
  has_bundle_slots?: boolean;
  duration_since_cds_ready_ms?: number;
  duration_since_graph_build_ms?: number;
};

export function trackKmCdsUiEvent(
  event: KmCdsUiAnalyticsEventNameV1,
  payload?: KmCdsUiAnalyticsPayloadV1 & Record<string, unknown>,
) {
  trackClientEvent(event, payload as Record<string, unknown>);
}
