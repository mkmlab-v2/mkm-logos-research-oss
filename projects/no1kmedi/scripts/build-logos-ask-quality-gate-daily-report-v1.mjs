/**
 * Logos Ask quality gate daily report.
 * - Aggregates S4 format gate + Azure distill decision metadata.
 * - Uses live battery queries as daily probe set.
 *
 * Usage:
 *   node ./scripts/build-logos-ask-quality-gate-daily-report-v1.mjs --base http://127.0.0.1:3010
 */
import { mkdirSync, readFileSync, writeFileSync, appendFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const workspaceRoot = path.resolve(__dirname, "../../..");
const contractPath = path.join(
  workspaceRoot,
  "docs/final/fixtures/logos_ask_quality_completion_contract_v1.json",
);

const base = (
  process.argv.find((a) => a.startsWith("--base="))?.slice(7) ||
  process.argv[process.argv.indexOf("--base") + 1] ||
  process.env.MKM_LOGOS_ASK_BASE_URL ||
  "http://127.0.0.1:3010"
).replace(/\/$/, "");

const timeoutArg =
  process.argv.find((a) => a.startsWith("--timeout-s="))?.slice(12) ??
  (() => {
    const idx = process.argv.indexOf("--timeout-s");
    return idx >= 0 ? process.argv[idx + 1] : undefined;
  })();
const timeoutSec = Number.parseInt(String(timeoutArg ?? "180"), 10);
const timeoutMs = Number.isFinite(timeoutSec) ? Math.max(30, timeoutSec) * 1000 : 180_000;

const outLatest =
  process.argv.find((a) => a.startsWith("--out="))?.slice(6) ||
  process.argv[process.argv.indexOf("--out") + 1] ||
  path.join(workspaceRoot, "reports/logos_ask_quality_gate_daily_report_v1_latest.json");

const outJsonl =
  process.argv.find((a) => a.startsWith("--jsonl="))?.slice(8) ||
  process.argv[process.argv.indexOf("--jsonl") + 1] ||
  path.join(workspaceRoot, "reports/logos_ask_quality_gate_daily_report_v1_log.jsonl");

function toShort(text, max = 220) {
  const raw = String(text || "").replace(/\s+/g, " ").trim();
  return raw.length <= max ? raw : `${raw.slice(0, max - 1)}…`;
}

function safeNum(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function scoreHeadline(summary) {
  const ratio = summary.format_gate.recomposed_rate;
  const leak = summary.s4_public_sanitize.leak_detected_rate;
  const azure = summary.azure_distill.applied_rate;
  if (ratio <= 0.3 && leak <= 0.1 && azure >= 0.2) return "healthy";
  if (ratio <= 0.5 && leak <= 0.2) return "watch";
  return "needs_attention";
}

async function callInquiry(query) {
  const res = await fetch(`${base}/api/logos-research/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(timeoutMs),
    body: JSON.stringify({
      query,
      output_format: "inquiry_report_v1",
      domain_lane: "logos",
      intent_chip: "reports",
      azure_distill_mode: "auto",
    }),
  });
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    return {
      ok: false,
      status: res.status,
      error: "invalid_json",
      preview: toShort(text),
    };
  }
  if (!res.ok || json?.ok === false) {
    return {
      ok: false,
      status: res.status,
      error: json?.error || "http_error",
      preview: toShort(text),
    };
  }
  const report = json?.report || {};
  const s4 = report?.sections?.S4 || {};
  const result = json?.result || {};
  const reportMeta = report?.azure_distill_meta || null;
  return {
    ok: true,
    status: res.status,
    query_mode: report?.query_mode || result?.query_mode || null,
    s4_body: s4?.body_ko || "",
    format_gate: s4?.format_gate || null,
    azure_distill_meta: reportMeta || result?.azure_distill_meta || null,
  };
}

async function main() {
  const contract = JSON.parse(readFileSync(contractPath, "utf8"));
  const queries = contract.live_battery_queries || [];
  const rows = [];

  for (const item of queries) {
    const query = String(item?.query_ko || "").trim();
    const res = await callInquiry(query);
    if (!res.ok) {
      rows.push({
        id: item?.id || null,
        query_ko: query,
        ok: false,
        status: res.status,
        error: res.error,
      });
      continue;
    }
    const formatGate = res.format_gate || {};
    const azureMeta = res.azure_distill_meta || {};
    rows.push({
      id: item?.id || null,
      query_ko: query,
      ok: true,
      status: res.status,
      query_mode: res.query_mode,
      format_gate: {
        applied: Boolean(formatGate.applied),
        recomposed: Boolean(formatGate.recomposed),
        missing_sections_count: Array.isArray(formatGate.missing_sections)
          ? formatGate.missing_sections.length
          : 0,
      },
      s4_public_sanitize: {
        leak_detected: /lemma:gnosis:|shared_lemma=|Lemma\s*연결\s*이웃\s*구절/i.test(res.s4_body),
      },
      azure_distill_meta: {
        attempted: Boolean(azureMeta.attempted),
        mode: azureMeta.mode || "auto",
        decision_reason: azureMeta.decision_reason || "unknown",
        decision_signal_count: safeNum(azureMeta.decision_signal_count, 0),
        applied: Boolean(azureMeta.applied),
      },
    });
  }

  const okRows = rows.filter((r) => r.ok);
  const total = rows.length;
  const okCount = okRows.length;
  const recomposedCount = okRows.filter((r) => r.format_gate?.recomposed).length;
  const appliedCount = okRows.filter((r) => r.format_gate?.applied).length;
  const leakCount = okRows.filter((r) => r.s4_public_sanitize?.leak_detected).length;
  const azureAttempted = okRows.filter((r) => r.azure_distill_meta?.attempted).length;
  const azureApplied = okRows.filter((r) => r.azure_distill_meta?.applied).length;

  const reasonCounts = {};
  for (const row of okRows) {
    const reason = row.azure_distill_meta?.decision_reason || "unknown";
    reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
  }

  const summary = {
    probe_total: total,
    probe_http_ok: okCount,
    format_gate: {
      applied_count: appliedCount,
      recomposed_count: recomposedCount,
      recomposed_rate: okCount ? Number((recomposedCount / okCount).toFixed(4)) : 0,
    },
    s4_public_sanitize: {
      leak_detected_count: leakCount,
      leak_detected_rate: okCount ? Number((leakCount / okCount).toFixed(4)) : 0,
    },
    azure_distill: {
      attempted_count: azureAttempted,
      applied_count: azureApplied,
      applied_rate: okCount ? Number((azureApplied / okCount).toFixed(4)) : 0,
      decision_reason_counts: reasonCounts,
    },
  };

  const report = {
    schema: "logos_ask_quality_gate_daily_report_v1",
    generated_at_utc: new Date().toISOString(),
    base,
    research_only: true,
    summary,
    posture: scoreHeadline(summary),
    rows,
  };

  mkdirSync(path.dirname(outLatest), { recursive: true });
  writeFileSync(outLatest, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  appendFileSync(outJsonl, `${JSON.stringify(report)}\n`, "utf8");

  console.log(
    JSON.stringify({
      ok: true,
      posture: report.posture,
      recomposed_rate: summary.format_gate.recomposed_rate,
      leak_detected_rate: summary.s4_public_sanitize.leak_detected_rate,
      azure_applied_rate: summary.azure_distill.applied_rate,
      out: outLatest,
      log: outJsonl,
    }),
  );
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: String(err) }));
  process.exit(1);
});
