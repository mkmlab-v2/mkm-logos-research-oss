import { NextResponse } from "next/server";
import { promises as fs } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";

const SUMMARY_PATH = path.join(
  process.cwd(),
  "memory",
  "commercialization",
  "km_cds_ui_events_daily_summary_latest.json",
);
const LOGOS_ECS_SUMMARY_PATH = path.join(
  process.cwd(),
  "docs",
  "final",
  "artifacts",
  "logos_studio_ecs_telemetry_summary_latest.json",
);
const LOGOS_FEEDBACK_SUMMARY_PATH = path.join(
  process.cwd(),
  "docs",
  "final",
  "artifacts",
  "logos_studio_feedback_summary_latest.json",
);

type KpiSummary = {
  schema?: string;
  generated_at_utc?: string;
  lookback_days?: number;
  counts_by_day?: Record<string, Record<string, number>>;
};

type DailyTrendPoint = {
  day: string;
  mount: number;
  ack: number;
  decline: number;
  admin_click_consumer: number;
  admin_click_safety: number;
  admin_reco_click_consumer: number;
  admin_reco_click_safety: number;
  ack_rate: number;
};

type LogosEcsSummary = {
  schema?: string;
  generated_at_utc?: string;
  window_days?: number;
  event_contract?: {
    event_name?: string;
    events_in_window?: number;
    ecs_observed_count?: number;
    ecs_missing_count?: number;
    ecs_observed_rate?: number;
  };
  ecs_stats?: {
    count?: number;
    min?: number;
    p10?: number;
    median?: number;
    mean?: number;
    p90?: number;
    max?: number;
  };
  band_counts?: Record<string, number>;
  query_mode_counts?: Record<string, number>;
  access_gate_counts?: Record<string, number>;
  research_only?: boolean;
  send_gate?: string;
  non_gating?: boolean;
};

type LogosFeedbackSummary = {
  schema?: string;
  generated_at_utc?: string;
  window_days?: number;
  counts?: { up?: number; down?: number; unknown?: number; total?: number };
  ratios?: { up_rate?: number; down_rate?: number; agreement_rate?: number };
  top_issue_types?: Record<string, number>;
  top_anchors?: Array<{ evidence_anchor?: string; total?: number; up?: number; down?: number }>;
  windows?: {
    w7?: {
      counts?: { up?: number; down?: number; unknown?: number; total?: number };
      ratios?: { up_rate?: number; down_rate?: number; agreement_rate?: number };
    };
    w30?: {
      counts?: { up?: number; down?: number; unknown?: number; total?: number };
      ratios?: { up_rate?: number; down_rate?: number; agreement_rate?: number };
    };
  };
  research_only?: boolean;
  send_gate?: string;
  non_gating?: boolean;
};

function countAlertDays(trend: DailyTrendPoint[]): number {
  return trend.filter((d) => d.ack_rate < 0.6).length;
}

function sumEvent(countsByDay: Record<string, Record<string, number>> | undefined, event: string): number {
  if (!countsByDay) return 0;
  let total = 0;
  for (const day of Object.keys(countsByDay)) {
    total += Number(countsByDay[day]?.[event] || 0);
  }
  return total;
}

function buildDailyTrend(countsByDay: Record<string, Record<string, number>>, days = 7): DailyTrendPoint[] {
  const keys = Object.keys(countsByDay).sort().slice(-days);
  return keys.map((day) => {
    const row = countsByDay[day] || {};
    const mount = Number(row.public_workspace_mount_v1 || 0);
    const ack = Number(row.public_mode_enter_ack_v1 || 0);
    const decline = Number(row.public_mode_enter_declined_v1 || 0);
    const adminClickConsumer = Number(row.admin_kpi_alert_click_consumer_v1 || 0);
    const adminClickSafety = Number(row.admin_kpi_alert_click_safety_v1 || 0);
    const adminRecoClickConsumer = Number(row.admin_kpi_reco_click_consumer_v1 || 0);
    const adminRecoClickSafety = Number(row.admin_kpi_reco_click_safety_v1 || 0);
    return {
      day,
      mount,
      ack,
      decline,
      admin_click_consumer: adminClickConsumer,
      admin_click_safety: adminClickSafety,
      admin_reco_click_consumer: adminRecoClickConsumer,
      admin_reco_click_safety: adminRecoClickSafety,
      ack_rate: mount > 0 ? Number((ack / mount).toFixed(4)) : 0,
    };
  });
}

export async function GET() {
  try {
    const [raw, ecsRaw, feedbackRaw] = await Promise.all([
      fs.readFile(SUMMARY_PATH, "utf8"),
      fs.readFile(LOGOS_ECS_SUMMARY_PATH, "utf8").catch(() => null),
      fs.readFile(LOGOS_FEEDBACK_SUMMARY_PATH, "utf8").catch(() => null),
    ]);
    const parsed = JSON.parse(raw) as KpiSummary;
    const ecs = ecsRaw ? (JSON.parse(ecsRaw) as LogosEcsSummary) : null;
    const feedback = feedbackRaw ? (JSON.parse(feedbackRaw) as LogosFeedbackSummary) : null;
    const counts = parsed.counts_by_day || {};
    const mount = sumEvent(counts, "public_workspace_mount_v1");
    const ack = sumEvent(counts, "public_mode_enter_ack_v1");
    const decline = sumEvent(counts, "public_mode_enter_declined_v1");
    const adminClickConsumer = sumEvent(counts, "admin_kpi_alert_click_consumer_v1");
    const adminClickSafety = sumEvent(counts, "admin_kpi_alert_click_safety_v1");
    const adminClickTotal = adminClickConsumer + adminClickSafety;
    const adminRecoClickConsumer = sumEvent(counts, "admin_kpi_reco_click_consumer_v1");
    const adminRecoClickSafety = sumEvent(counts, "admin_kpi_reco_click_safety_v1");
    const adminRecoClickTotal = adminRecoClickConsumer + adminRecoClickSafety;
    const adminChecklistToggleTotal = sumEvent(counts, "admin_kpi_checklist_toggle_v1");
    const adminPriorityActionShowTotal = sumEvent(counts, "admin_kpi_priority_action_show_v1");
    const adminPriorityActionClickTotal = sumEvent(counts, "admin_kpi_priority_action_click_v1");
    const ackRate = mount > 0 ? Number((ack / mount).toFixed(4)) : 0;
    const trend7d = buildDailyTrend(counts, 7);
    const alertDays = countAlertDays(trend7d);
    const alertClickRate = alertDays > 0 ? Number((adminClickTotal / alertDays).toFixed(4)) : 0;
    const alertRecoClickRate = alertDays > 0 ? Number((adminRecoClickTotal / alertDays).toFixed(4)) : 0;
    const priorityActionExecRate =
      adminPriorityActionShowTotal > 0
        ? Number((adminPriorityActionClickTotal / adminPriorityActionShowTotal).toFixed(4))
        : 0;
    return NextResponse.json(
      {
        success: true,
        schema: parsed.schema || "km_cds_ui_events_daily_summary_v1",
        generated_at_utc: parsed.generated_at_utc || null,
        lookback_days: parsed.lookback_days || 7,
        kpi: {
          public_workspace_mount: mount,
          public_mode_ack: ack,
          public_mode_decline: decline,
          public_ack_rate: ackRate,
          admin_alert_click_consumer: adminClickConsumer,
          admin_alert_click_safety: adminClickSafety,
          admin_alert_days_7d: alertDays,
          admin_alert_clicks_total: adminClickTotal,
          admin_alert_click_rate_per_alert_day: alertClickRate,
          admin_reco_click_consumer: adminRecoClickConsumer,
          admin_reco_click_safety: adminRecoClickSafety,
          admin_reco_clicks_total: adminRecoClickTotal,
          admin_reco_click_rate_per_alert_day: alertRecoClickRate,
          admin_checklist_toggle_total: adminChecklistToggleTotal,
          admin_priority_action_show_total: adminPriorityActionShowTotal,
          admin_priority_action_click_total: adminPriorityActionClickTotal,
          admin_priority_action_exec_rate: priorityActionExecRate,
        },
        trend_7d: trend7d,
        logos_studio_ecs: ecs
          ? {
              schema: ecs.schema ?? "logos_studio_ecs_telemetry_summary_v1",
              generated_at_utc: ecs.generated_at_utc ?? null,
              window_days: ecs.window_days ?? 30,
              event_contract: ecs.event_contract ?? null,
              ecs_stats: ecs.ecs_stats ?? null,
              band_counts: ecs.band_counts ?? {},
              query_mode_counts: ecs.query_mode_counts ?? {},
              access_gate_counts: ecs.access_gate_counts ?? {},
              research_only: ecs.research_only ?? true,
              send_gate: ecs.send_gate ?? "HOLD",
              non_gating: ecs.non_gating ?? true,
            }
          : null,
        logos_studio_feedback: feedback
          ? {
              schema: feedback.schema ?? "logos_studio_feedback_summary_v1",
              generated_at_utc: feedback.generated_at_utc ?? null,
              window_days: feedback.window_days ?? 30,
              counts: feedback.counts ?? { up: 0, down: 0, unknown: 0, total: 0 },
              ratios: feedback.ratios ?? { up_rate: 0, down_rate: 0, agreement_rate: 0 },
              top_issue_types: feedback.top_issue_types ?? {},
              top_anchors: feedback.top_anchors ?? [],
              windows: feedback.windows ?? null,
              research_only: feedback.research_only ?? true,
              send_gate: feedback.send_gate ?? "HOLD",
              non_gating: feedback.non_gating ?? true,
            }
          : null,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch {
    return NextResponse.json(
      {
        success: false,
        error: "summary_not_ready",
      },
      { status: 404, headers: { "Cache-Control": "no-store" } },
    );
  }
}

