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
    const raw = await fs.readFile(SUMMARY_PATH, "utf8");
    const parsed = JSON.parse(raw) as KpiSummary;
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

