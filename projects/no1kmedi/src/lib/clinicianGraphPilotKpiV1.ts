/**
 * Clinician graph pilot KPI — client timing + telemetry (PHI-free).
 */

import { trackKmCdsUiEvent, KM_CDS_UI_ANALYTICS_EVENTS_V1 } from "./km-cds-ui-analytics-events-v1";

const STORAGE_KEY = "mkm_clinician_graph_pilot_timing_v1";

type TimingRow = {
  encounter_ref: string;
  cds_ready_ms?: number;
  graph_build_ms?: number;
  signoff_ms?: number;
};

function readAll(): Record<string, TimingRow> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, TimingRow>;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeAll(rows: Record<string, TimingRow>) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
  } catch {
    // ignore quota
  }
}

function upsert(encounterRef: string, patch: Partial<TimingRow>) {
  const key = encounterRef.trim();
  if (!key) return;
  const rows = readAll();
  rows[key] = { ...rows[key], ...patch, encounter_ref: key };
  writeAll(rows);
}

export function markClinicianGraphCdsReady(encounterRef: string) {
  upsert(encounterRef, { cds_ready_ms: Date.now() });
}

export function trackClinicianGraphBuild(encounterRef: string, payload: {
  node_count: number;
  edge_count: number;
  conflict_group_count: number;
  has_bundle_slots: boolean;
}) {
  const now = Date.now();
  const rows = readAll();
  const row = rows[encounterRef];
  upsert(encounterRef, { graph_build_ms: now });
  trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.CLINICIAN_GRAPH_BUILD_V1, {
    surface: "workspace",
    encounter_ref: encounterRef,
    node_count: payload.node_count,
    edge_count: payload.edge_count,
    conflict_group_count: payload.conflict_group_count,
    has_bundle_slots: payload.has_bundle_slots,
    duration_since_cds_ready_ms: row?.cds_ready_ms ? now - row.cds_ready_ms : undefined,
  });
}

export function trackClinicianGraphViewMode(encounterRef: string, viewMode: "list" | "graph") {
  trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.CLINICIAN_GRAPH_VIEW_MODE_V1, {
    surface: "workspace",
    encounter_ref: encounterRef,
    view_mode: viewMode,
  });
}

export function trackClinicianGraphReviewFeedback(encounterRef: string, payload: {
  target_id: string;
  feedback: "up" | "down" | "hold";
  reason_code?: string;
}) {
  trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.CLINICIAN_GRAPH_REVIEW_FEEDBACK_V1, {
    surface: "workspace",
    encounter_ref: encounterRef,
    target_id: payload.target_id,
    feedback: payload.feedback,
    reason_code: payload.reason_code,
  });
}

export function trackClinicianGraphSignoff(encounterRef: string) {
  const now = Date.now();
  const rows = readAll();
  const row = rows[encounterRef];
  upsert(encounterRef, { signoff_ms: now });
  const durationSinceGraphMs = row?.graph_build_ms ? now - row.graph_build_ms : undefined;
  const durationSinceCdsMs = row?.cds_ready_ms ? now - row.cds_ready_ms : undefined;
  trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.CLINICIAN_GRAPH_SIGNOFF_V1, {
    surface: "workspace",
    encounter_ref: encounterRef,
  });
  trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.CLINICIAN_GRAPH_REVIEW_TIMING_V1, {
    surface: "workspace",
    encounter_ref: encounterRef,
    duration_since_graph_build_ms: durationSinceGraphMs,
    duration_since_cds_ready_ms: durationSinceCdsMs,
  });
}
