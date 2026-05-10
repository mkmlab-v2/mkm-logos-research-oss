#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";

const CWD = process.cwd();
const eventsPath = path.join(CWD, "memory", "commercialization", "hub_events.jsonl");
const outPath = path.join(CWD, "memory", "commercialization", "km_cds_ui_events_daily_summary_latest.json");
const lookbackDays = Number(process.argv[2] || "7");
const sinceTs = Date.now() - Math.max(1, lookbackDays) * 24 * 60 * 60 * 1000;

const tracked = new Set([
  "public_workspace_mount_v1",
  "public_mode_enter_ack_v1",
  "public_mode_enter_declined_v1",
  "public_mode_exit",
  "cds_mode_enter",
  "cds_mode_exit",
  "admin_kpi_alert_click_consumer_v1",
  "admin_kpi_alert_click_safety_v1",
  "admin_kpi_reco_click_consumer_v1",
  "admin_kpi_reco_click_safety_v1",
  "admin_kpi_checklist_toggle_v1",
  "admin_kpi_priority_action_show_v1",
  "admin_kpi_priority_action_click_v1",
]);

function ymd(iso) {
  if (!iso || typeof iso !== "string") return "unknown";
  return iso.slice(0, 10);
}

async function main() {
  let raw = "";
  try {
    raw = await fs.readFile(eventsPath, "utf8");
  } catch {
    const empty = {
      schema: "km_cds_ui_events_daily_summary_v1",
      generated_at_utc: new Date().toISOString(),
      lookback_days: lookbackDays,
      source: eventsPath,
      counts_by_day: {},
      note: "events file not found",
    };
    await fs.mkdir(path.dirname(outPath), { recursive: true });
    await fs.writeFile(outPath, `${JSON.stringify(empty, null, 2)}\n`, "utf8");
    console.log(`wrote ${outPath}`);
    return;
  }

  const counts = {};
  for (const line of raw.split(/\r?\n/)) {
    if (!line.trim()) continue;
    let row;
    try {
      row = JSON.parse(line);
    } catch {
      continue;
    }
    const event = String(row.event || "");
    if (!tracked.has(event)) continue;
    const ts = String(row.ts_utc || "");
    const t = Date.parse(ts);
    if (!Number.isFinite(t) || t < sinceTs) continue;
    const day = ymd(ts);
    counts[day] ||= {};
    counts[day][event] = (counts[day][event] || 0) + 1;
  }

  const result = {
    schema: "km_cds_ui_events_daily_summary_v1",
    generated_at_utc: new Date().toISOString(),
    lookback_days: lookbackDays,
    source: eventsPath,
    tracked_events: Array.from(tracked),
    counts_by_day: counts,
  };

  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await fs.writeFile(outPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  console.log(`wrote ${outPath}`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(2);
});

