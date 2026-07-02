/**
 * Live Ask battery — P0 queries snapshot after deploy.
 * Usage: node scripts/smoke-logos-ask-live-battery-v1.mjs [--base URL] [--out path]
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const workspaceRoot = path.resolve(__dirname, "../../..");
const contractPath = path.join(
  workspaceRoot,
  "docs/final/fixtures/logos_ask_quality_completion_contract_v1.json",
);

function stripPublicResearchTags(text) {
  return (text || "")
    .replace(/\[HYPO\]\s*/gi, "")
    .replace(/\[NON_GATING\]\s*/gi, "")
    .replace(/\bresearch_only\b/gi, "")
    .replace(/\bsend_gate\s*:\s*\w+/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function splitS4PublicBody(body) {
  const raw = (body || "").trim();
  if (!raw) return { narrative: "", readingPack: "" };
  const parts = raw.split(/(?:^|\n|\s)---(?:\s|\n)|###\s*Reading pack/i);
  return {
    narrative: stripPublicResearchTags((parts[0] ?? "").trim()),
    readingPack: stripPublicResearchTags(parts.slice(1).join("\n").trim()),
  };
}

const base = (
  process.argv.find((a) => a.startsWith("--base="))?.slice(7) ||
  process.argv[process.argv.indexOf("--base") + 1] ||
  process.env.MKM_LOGOS_ASK_BASE_URL ||
  "https://jema-ai.com"
).replace(/\/$/, "");

const outArg =
  process.argv.find((a) => a.startsWith("--out="))?.slice(6) ||
  process.argv[process.argv.indexOf("--out") + 1] ||
  path.join(workspaceRoot, "reports/logos_ask_live_battery_v1_latest.json");

const contract = JSON.parse(readFileSync(contractPath, "utf8"));
const queries = contract.live_battery_queries || [];

const DOGMA_RE =
  /(반드시|확실히|단정|투자\s*시그널|매수|매도|적그리스도는\s*바로|666은\s*반드시)/i;
const GUARD_RE = /topic_mismatch|억지\s*연결|직접\s*대응하지\s*않습니다|재질의를\s*권합니다/i;

function hasAnchor(text, refs) {
  const t = text.replace(/\s/g, "").toLowerCase();
  return (refs || []).some((ref) => {
    const r = String(ref).replace(/\s/g, "").toLowerCase();
    const book = r.split(".")[0];
    return t.includes(r) || t.includes(book.toLowerCase());
  });
}

function scoreRow(item, bodyRaw, presetId, queryMode) {
  const { narrative } = splitS4PublicBody(bodyRaw || "");
  const publicText = stripPublicResearchTags(narrative || bodyRaw || "");
  const isGuard =
    String(queryMode || "").includes("topic_mismatch_guard") || GUARD_RE.test(publicText);
  const forbidden = item.forbidden_preset_ids || [];
  const presetBad = forbidden.includes(presetId);
  const anchorOk = hasAnchor(publicText, item.gold_primary_refs);
  const paragraphs = publicText.split(/\n+/).filter((p) => p.trim().length > 20);
  const narrativeOk = publicText.length >= 120 && paragraphs.length >= 2;
  const tagsOk = !/\[HYPO\]|\[NON_GATING\]|research_only|send_gate/i.test(publicText);
  const dogmaOk = !DOGMA_RE.test(publicText);
  const guardOnlyFail = Boolean(item.reject_guard_only) && isGuard;
  const qualityPass =
    !presetBad && !guardOnlyFail && anchorOk && narrativeOk && tagsOk && dogmaOk;
  return {
    id: item.id,
    query_ko: item.query_ko,
    quality_tier: item.quality_tier,
    preset_id: presetId ?? null,
    query_mode: queryMode ?? null,
    topic_mismatch_guard: isGuard,
    public_preview_200: publicText.slice(0, 200),
    checks: {
      preset_ok: !presetBad,
      anchor_ok: anchorOk,
      narrative_ok: narrativeOk,
      public_tags_ok: tagsOk,
      dogma_ok: dogmaOk,
      guard_only_ok: !guardOnlyFail,
    },
    quality_pass: qualityPass,
  };
}

async function fetchInquiry(query) {
  const res = await fetch(`${base}/api/logos-research/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      output_format: "inquiry_report_v1",
      domain_lane: "logos",
      intent_chip: "reports",
    }),
  });
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    return { ok: false, status: res.status, error: "invalid_json", preview: text.slice(0, 200) };
  }
  if (!res.ok) {
    return { ok: false, status: res.status, error: json.error || "http_error", json };
  }
  const report = json.report || {};
  const body = report.sections?.S4?.body_ko || "";
  return {
    ok: true,
    status: res.status,
    preset_id: report.preset_id,
    query_mode: report.query_mode,
    body,
  };
}

async function main() {
  const rows = [];
  for (const item of queries) {
    const result = await fetchInquiry(item.query_ko);
    if (!result.ok) {
      rows.push({
        id: item.id,
        query_ko: item.query_ko,
        http_ok: false,
        status: result.status,
        error: result.error,
        quality_pass: false,
      });
      continue;
    }
    const scored = scoreRow(item, result.body, result.preset_id, result.query_mode);
    rows.push({ ...scored, http_ok: true, status: result.status });
  }

  const p0 = rows.filter((r) => {
    const q = queries.find((x) => x.id === r.id);
    return String(q?.quality_tier || "").startsWith("P0");
  });
  const p0Pass = p0.filter((r) => r.quality_pass).length;
  const allPass = rows.filter((r) => r.quality_pass).length;
  const passRate = rows.length ? allPass / rows.length : 0;
  const p0Rate = p0.length ? p0Pass / p0.length : 0;
  const minRate = contract.gates?.live_battery_pass_rate_min ?? 0.6;

  const report = {
    schema: "logos_ask_live_battery_v1",
    generated_at_utc: new Date().toISOString(),
    base,
    research_only: true,
    items_total: rows.length,
    items_passed: allPass,
    pass_rate: Math.round(passRate * 10000) / 10000,
    p0_pass_rate: Math.round(p0Rate * 10000) / 10000,
    gate_min_pass_rate: minRate,
    quality_ok: passRate >= minRate,
    rows,
  };

  mkdirSync(path.dirname(outArg), { recursive: true });
  writeFileSync(outArg, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(
    JSON.stringify({
      ok: report.quality_ok,
      pass_rate: report.pass_rate,
      p0_pass_rate: report.p0_pass_rate,
      out: outArg,
    }),
  );
  process.exit(report.quality_ok ? 0 : 1);
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: String(err) }));
  process.exit(1);
});
