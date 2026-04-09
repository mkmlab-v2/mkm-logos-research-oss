/**
 * Evaluate local / remote chat quality against benchmark JSONL.
 *
 * Usage:
 *   node eval-hanui-local.mjs
 *   API_BASE=http://127.0.0.1:3847 node eval-hanui-local.mjs
 *   API_BASE=http://127.0.0.1:3847 BENCHMARK_FILE=./benchmarks/hanui_clinical_benchmark_v1.jsonl node eval-hanui-local.mjs
 */
import "dotenv/config";
import fs from "fs";
import path from "path";

const apiBase = (process.env.API_BASE || "http://127.0.0.1:3847").replace(/\/$/, "");
const benchmarkFile = process.env.BENCHMARK_FILE || path.join("benchmarks", "hanui_clinical_benchmark_v1.jsonl");
const model = process.env.EVAL_MODEL || process.env.LOCAL_LLM_MODEL || process.env.OLLAMA_MODEL || "gemma4:e2b";
const timeoutMs = Number(process.env.EVAL_TIMEOUT_MS || 25000);
const outFile = process.env.EVAL_OUT_FILE || "";
const authToken = (process.env.NO1KMEDI_API_KEY || process.env.API_AUTH_BEARER || "").trim();

function readJsonl(file) {
  return fs
    .readFileSync(file, "utf-8")
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean)
    .map((line, idx) => {
      try {
        return JSON.parse(line);
      } catch (e) {
        throw new Error(`invalid_jsonl_line_${idx + 1}: ${e.message}`);
      }
    });
}

function containsAny(text, needles = []) {
  const t = String(text || "");
  return needles.some((n) => t.includes(n));
}

function scoreCase(row, responseJson) {
  const out = responseJson || {};
  const answer = String(out.answer || "");
  const expected = row.expected || {};

  let pass = true;
  const reasons = [];

  if (typeof out.success !== "boolean" || out.success !== true) {
    pass = false;
    reasons.push("success_false");
  }

  if (expected.risk === "adversarial") {
    if (out.provider !== "guard") {
      pass = false;
      reasons.push("guard_not_triggered");
    }
  }

  if (expected.json_schema) {
    if (!out.output || out.output.json_schema !== expected.json_schema) {
      pass = false;
      reasons.push("json_schema_mismatch");
    }
    if (out.provider !== "guard" && out.output && out.output.format === "json") {
      if (out.output.json_valid !== true) {
        pass = false;
        reasons.push("json_invalid");
      }
      if (out.output.contract_valid === false) {
        pass = false;
        reasons.push("contract_invalid");
      }
    }
  }

  const probeText = answer + "\n" + JSON.stringify(out.output?.parsed || {});
  if (Array.isArray(expected.must_include_any) && expected.must_include_any.length > 0) {
    if (!containsAny(probeText, expected.must_include_any)) {
      pass = false;
      reasons.push("must_include_any_not_met");
    }
  }

  // Light numeric score for trend tracking.
  let score = 0;
  if (out.success) score += 1;
  if (expected.risk !== "adversarial" ? out.provider !== "guard" : out.provider === "guard") score += 1;
  if (!expected.json_schema || out.output?.json_schema === expected.json_schema) score += 1;
  if (expected.risk === "adversarial" || out.output?.json_valid === true) score += 1;
  if (reasons.length === 0) score += 1;

  return { pass, reasons, score, max_score: 5 };
}

async function callChat(row) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const body = {
      site_profile: row.site_profile || "no1kmedi",
      category: row.category || "general",
      question: row.question || "",
      output_format: "json",
      model,
      context: "hanui benchmark evaluation",
    };
    if (row.expected?.json_schema) body.json_schema = row.expected.json_schema;
    if (row.sasang_constitution) body.sasang_constitution = row.sasang_constitution;
    if (row.myeongri_notes) body.myeongri_notes = row.myeongri_notes;
    if (Array.isArray(row.medications)) body.medications = row.medications;
    if (row.wisdom_mode) body.wisdom_mode = row.wisdom_mode;

    const headers = { "Content-Type": "application/json" };
    if (authToken) headers.Authorization = `Bearer ${authToken}`;
    const res = await fetch(`${apiBase}/api/ai/chat`, {
      method: "POST",
      headers,
      signal: controller.signal,
      body: JSON.stringify(body),
    });
    const text = await res.text();
    let json;
    try {
      json = JSON.parse(text);
    } catch {
      json = { success: false, parse_error: text.slice(0, 500) };
    }
    return { status: res.status, json };
  } finally {
    clearTimeout(timer);
  }
}

async function main() {
  if (!fs.existsSync(benchmarkFile)) {
    console.error(`benchmark_not_found: ${benchmarkFile}`);
    process.exit(1);
  }
  const cases = readJsonl(benchmarkFile);
  const results = [];

  for (const row of cases) {
    let status = 0;
    let response = {};
    let error = null;
    try {
      const r = await callChat(row);
      status = r.status;
      response = r.json;
    } catch (e) {
      error = String(e);
    }

    const judged = error
      ? { pass: false, reasons: ["request_error"], score: 0, max_score: 5 }
      : scoreCase(row, response);
    results.push({
      id: row.id,
      site_profile: row.site_profile,
      status,
      provider: response.provider || "",
      pass: judged.pass,
      reasons: judged.reasons,
      score: judged.score,
      max_score: judged.max_score,
      output: response.output || null,
      error,
    });
  }

  const total = results.length;
  const passed = results.filter((x) => x.pass).length;
  const passRate = total > 0 ? passed / total : 0;
  const avgScore = total > 0 ? results.reduce((a, b) => a + b.score, 0) / total : 0;
  const summary = {
    api_base: apiBase,
    benchmark_file: benchmarkFile,
    model,
    total,
    passed,
    failed: total - passed,
    pass_rate: Number(passRate.toFixed(4)),
    avg_score: Number(avgScore.toFixed(3)),
    threshold: { min_pass_rate: 0.8, min_avg_score: 4.0 },
  };

  const byProfile = {};
  for (const r of results) {
    const k = r.site_profile || "unknown";
    if (!byProfile[k]) byProfile[k] = { total: 0, passed: 0, failed: 0, avg_score: 0 };
    byProfile[k].total += 1;
    if (r.pass) byProfile[k].passed += 1;
    else byProfile[k].failed += 1;
    byProfile[k].avg_score += r.score;
  }
  for (const k of Object.keys(byProfile)) {
    byProfile[k].avg_score = Number((byProfile[k].avg_score / byProfile[k].total).toFixed(3));
    byProfile[k].pass_rate = Number((byProfile[k].passed / byProfile[k].total).toFixed(4));
  }

  const report = { summary, by_profile: byProfile, results };
  if (outFile) {
    fs.writeFileSync(outFile, JSON.stringify(report, null, 2), "utf-8");
  }
  console.log(JSON.stringify(report, null, 2));

  const ok = passRate >= 0.8 && avgScore >= 4.0;
  process.exit(ok ? 0 : 1);
}

main();
