import dotenv from "dotenv";
import express from "express";
import { existsSync } from "fs";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";
import crypto from "crypto";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const workspaceRootEnv = path.join(__dirname, "..", "..", "..", ".env");
const packageEnv = path.join(__dirname, ".env");
if (existsSync(workspaceRootEnv)) dotenv.config({ path: workspaceRootEnv });
if (existsSync(packageEnv)) dotenv.config({ path: packageEnv });

const app = express();
const PORT = process.env.PORT || 3000;
const ADMIN_TOKEN = process.env.NO1KMEDI_ADMIN_TOKEN || "NO1KMEDI_2026_xF7pQ2mL9vR4kT8sW1dH6nC3bY5uJ0aZ";
const N8N_WEBHOOK_URL = process.env.N8N_WEBHOOK_URL || "";
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || "";
const OPENROUTER_MODEL = process.env.OPENROUTER_MODEL || "openai/gpt-4.1-mini";

/** Same convention as workspace `.env.example`: Ollama OpenAI-compatible endpoint. */
function deriveLocalLlmUrl() {
  const explicit = String(process.env.LOCAL_LLM_URL || "").trim();
  if (explicit) return explicit;
  const host = String(process.env.OLLAMA_HOST || "")
    .trim()
    .replace(/\/$/, "");
  if (host) return `${host}/v1/chat/completions`;
  return "";
}

function deriveLocalLlmDefaultModel() {
  const m = String(process.env.LOCAL_LLM_MODEL || process.env.OLLAMA_MODEL || "").trim();
  return m || "gemma4:e2b";
}

const LOCAL_LLM_URL = deriveLocalLlmUrl();
const LOCAL_LLM_DEFAULT_MODEL = deriveLocalLlmDefaultModel();
const AI_ROUTER_MODE = (process.env.AI_ROUTER_MODE || "hybrid").toLowerCase(); // n8n|openrouter|local|hybrid
/** Set AI_CHAT_GUARDS=0 to disable adversarial block + CoT stripping (debug only). */
const AI_CHAT_GUARDS = process.env.AI_CHAT_GUARDS !== "0";

function envInt(name, def, min, max) {
  const v = parseInt(String(process.env[name] || ""), 10);
  if (!Number.isFinite(v)) return def;
  return Math.min(max, Math.max(min, v));
}

/** n8n webhook fetch: fail fast so hybrid can fall through (ms). */
const N8N_FETCH_TIMEOUT_MS = envInt("N8N_FETCH_TIMEOUT_MS", 12000, 1000, 120000);
const OPENROUTER_FETCH_TIMEOUT_MS = envInt("OPENROUTER_FETCH_TIMEOUT_MS", 60000, 5000, 180000);
/** Matches .env.example LOCAL_LLM_TIMEOUT_MS (alias LOCAL_LLM_FETCH_TIMEOUT_MS). */
const LOCAL_LLM_FETCH_TIMEOUT_MS = envInt(
  "LOCAL_LLM_FETCH_TIMEOUT_MS",
  envInt("LOCAL_LLM_TIMEOUT_MS", 120000, 3000, 600000),
  3000,
  600000
);

/**
 * @param {string} url
 * @param {RequestInit} init
 * @param {number} timeoutMs
 */
async function fetchWithTimeout(url, init, timeoutMs) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(t);
  }
}

function effectiveAiRouterMode(site_profile) {
  if (site_profile === "mkmlife") {
    const m = String(process.env.MKMLIFE_AI_ROUTER_MODE || "")
      .trim()
      .toLowerCase();
    if (m && ["n8n", "openrouter", "local", "hybrid"].includes(m)) return m;
  }
  return AI_ROUTER_MODE;
}

/**
 * @param {"mkmlife"|"no1kmedi"} site_profile
 * @param {string|undefined} requestedModel
 * @param {"openrouter"|"local"} backend
 */
function pickModelForBackend(site_profile, requestedModel, backend) {
  const req = requestedModel && String(requestedModel).trim();
  if (req) return req;
  if (site_profile === "mkmlife") {
    if (backend === "openrouter") {
      const m = String(process.env.MKMLIFE_OPENROUTER_MODEL || "").trim();
      if (m) return m;
    }
    if (backend === "local") {
      const m = String(process.env.MKMLIFE_LOCAL_LLM_MODEL || "").trim();
      if (m) return m;
    }
  }
  return "";
}

function slugRouterError(e) {
  const msg = (e && e.message) || String(e || "error");
  return msg.replace(/\s+/g, "_").slice(0, 72);
}

function hasAiBackendConfigured() {
  const m = AI_ROUTER_MODE;
  if (m === "n8n") return !!N8N_WEBHOOK_URL;
  if (m === "openrouter") return !!OPENROUTER_API_KEY;
  if (m === "local") return !!LOCAL_LLM_URL;
  return !!(N8N_WEBHOOK_URL || LOCAL_LLM_URL || OPENROUTER_API_KEY);
}

/** n8n Webhook Request Contract — bump when breaking payload shape */
const N8N_CONTRACT_VERSION = "1.0";

const HANUI_SYSTEM_PROMPT = [
  "You are a Korean medicine clinical support assistant, not a licensed clinician.",
  "Never provide definitive diagnosis or a concrete herbal prescription.",
  "If emergency is suspected, tell the user to call 119 or go to the ER immediately.",
  "State AI limitations briefly. Respond in Korean unless the user asks otherwise.",
  "Do not role-play as a physician or hide disclaimers when they are required for safety.",
].join(" ");

/** @param {string|undefined} raw */
function normalizeSiteProfile(raw) {
  const v = String(raw || "")
    .toLowerCase()
    .trim()
    .replace(/\.com$/i, "");
  if (v === "mkmlife") return "mkmlife";
  return "no1kmedi";
}

const MKMLIFE_SYSTEM_PROMPT = [
  HANUI_SYSTEM_PROMPT,
  "Audience: general public (mkmlife.com). Explanations stay short, clear, and cautious.",
  "Avoid deep professional syndrome differentiation unless the user explicitly asks.",
].join(" ");

const NO1KMEDI_CLINICAL_SYSTEM_PROMPT = [
  HANUI_SYSTEM_PROMPT,
  "Audience: licensed Korean medicine clinicians (no1kmedi.com).",
  "Discuss pattern differentiation only as hypotheses with distinguishing questions, not as a definitive diagnosis.",
  "For plain-text replies, structure Korean output with headings:",
  "1) 요약 2) 변증/감별 가설 3) 안전·병용 체크 4) 근거·한계 5) 다음 진료 액션.",
].join(" ");

/** @param {"mkmlife"|"no1kmedi"} profile */
function systemPromptForProfile(profile) {
  return profile === "mkmlife" ? MKMLIFE_SYSTEM_PROMPT : NO1KMEDI_CLINICAL_SYSTEM_PROMPT;
}

const JSON_OUTPUT_HINT =
  "\n[OUTPUT] Respond with a single JSON object only. No markdown fences, no explanatory text before or after the JSON.";

function scoreRagEntry(question, entry) {
  const q = String(question || "").toLowerCase();
  const text = String(entry.text_ko || "").toLowerCase();
  const tags = (entry.tags || []).join(" ").toLowerCase();
  const hay = `${text} ${tags}`;
  let score = 0;
  for (const w of q.split(/\s+/)) {
    if (w.length < 2) continue;
    if (hay.includes(w)) score++;
  }
  return score;
}

async function retrieveHanuiRagLite(question, topK = 3) {
  const entries = await readJson(path.join(dataDir, "hanui_rag_lite.json"), []);
  if (!Array.isArray(entries) || entries.length === 0) {
    return { text: "", hits: [] };
  }
  const scored = entries
    .map((e) => ({ e, s: scoreRagEntry(question, e) }))
    .sort((a, b) => b.s - a.s)
    .filter((x) => x.s > 0)
    .slice(0, topK);
  const lines = scored.map((x) => `- [${x.e.id}|${x.e.source_label}] ${x.e.text_ko}`);
  return {
    text: lines.join("\n"),
    hits: scored.map((x) => ({ id: x.e.id, score: x.s, source_label: x.e.source_label })),
  };
}

/**
 * @param {"mkmlife"|"no1kmedi"} profile
 * @param {string} output_format
 * @param {string|undefined} rawSchema
 */
function resolveJsonSchema(profile, output_format, rawSchema) {
  if (output_format !== "json") return null;
  const s = String(rawSchema || "")
    .trim()
    .toLowerCase();
  if (s === "hanui_clinical_v1" || s === "hanui_fusion_v2" || s === "mkmlife_consumer_v1") return s;
  if (s) return s;
  return profile === "mkmlife" ? "mkmlife_consumer_v1" : "hanui_clinical_v1";
}

/**
 * @param {string|null} jsonSchema
 */
function jsonSchemaHint(jsonSchema) {
  if (!jsonSchema) return "";
  if (jsonSchema === "hanui_clinical_v1") {
    return `${JSON_OUTPUT_HINT}
Use this exact JSON shape (no extra keys at root; arrays may be empty):
{"schema":"hanui_clinical_v1","summary_ko":"","differential_hypotheses":[{"pattern_ko":"","rationale_ko":"","distinguishing_questions":[]}],"red_flags_ko":[],"interaction_checks_ko":[],"evidence_notes":[{"note_ko":"","level":"A|B|C|요약"}],"patient_education_ko":"","next_steps_ko":[],"limitations_ko":""}`;
  }
  if (jsonSchema === "hanui_fusion_v2") {
    return `${JSON_OUTPUT_HINT}
Use this exact JSON shape:
{"schema":"hanui_fusion_v2","summary_ko":"","sasang_hypothesis":{"constitution_ko":"","confidence":"low|medium|high","rationale_ko":""},"myeongri_risk_tags":[{"tag_ko":"","rationale_ko":""}],"neutralized_wisdom_actions":[{"theme_ko":"","action_ko":"","tone":"secular"}],"drug_interaction_matrix":[{"drug_or_class":"","risk_note_ko":"","monitoring_ko":""}],"differential_hypotheses":[{"pattern_ko":"","rationale_ko":"","distinguishing_questions":[]}],"evidence_citations":[{"title":"","summary_ko":"","level":"A|B|C|요약"}],"patient_plan_ko":{"daily":"", "weekly":"", "when_to_seek_care":""},"limitations_ko":""}
NEVER use Korean root keys like "요약", "근거·한계", "다음 진료 액션". Use exact keys only.`;
  }
  if (jsonSchema === "mkmlife_consumer_v1") {
    return `${JSON_OUTPUT_HINT}
Use this exact JSON shape (required root keys only):
{"schema":"mkmlife_consumer_v1","summary_ko":"","caution_ko":"","when_to_seek_care_ko":""}
Content rules for summary_ko (single string, use newline separation):
- Line block 1: 3-line user-facing summary (concise Korean).
- Line block 2: evidence/limitations (what is uncertain; no definitive diagnosis).
- Line block 3: 7-day self-observation plan as numbered lines 1)–7) (non-prescriptive habits only).
Optional extra root keys (if present, must match types; omit if unsure):
- "evidence_bullets_ko": string[] (max 5 short bullets)
- "seven_day_actions_ko": string[] (length 7; daily micro-actions)`;
  }
  return JSON_OUTPUT_HINT;
}

/**
 * @param {object} parsed
 * @param {string|null} jsonSchema
 */
function validateJsonContract(parsed, jsonSchema) {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { valid: false, errors: ["root_not_object"] };
  }
  const errors = [];
  if (jsonSchema === "hanui_clinical_v1") {
    if (parsed.schema !== "hanui_clinical_v1") errors.push("schema_field_mismatch");
    if (!String(parsed.summary_ko || "").trim()) errors.push("missing_summary_ko");
    if (!Array.isArray(parsed.differential_hypotheses)) errors.push("differential_hypotheses_not_array");
  } else if (jsonSchema === "hanui_fusion_v2") {
    if (parsed.schema !== "hanui_fusion_v2") errors.push("schema_field_mismatch");
    if (!String(parsed.summary_ko || "").trim()) errors.push("missing_summary_ko");
    if (!parsed.sasang_hypothesis || typeof parsed.sasang_hypothesis !== "object")
      errors.push("missing_sasang_hypothesis");
    if (!Array.isArray(parsed.myeongri_risk_tags)) errors.push("myeongri_risk_tags_not_array");
    if (!Array.isArray(parsed.neutralized_wisdom_actions)) errors.push("neutralized_wisdom_actions_not_array");
    if (!Array.isArray(parsed.drug_interaction_matrix)) errors.push("drug_interaction_matrix_not_array");
    if (!Array.isArray(parsed.evidence_citations)) errors.push("evidence_citations_not_array");
    if (!parsed.patient_plan_ko || typeof parsed.patient_plan_ko !== "object") errors.push("missing_patient_plan_ko");
  } else if (jsonSchema === "mkmlife_consumer_v1") {
    if (parsed.schema !== "mkmlife_consumer_v1") errors.push("schema_field_mismatch");
    if (!String(parsed.summary_ko || "").trim()) errors.push("missing_summary_ko");
    if (!String(parsed.caution_ko || "").trim()) errors.push("missing_caution_ko");
    if (!String(parsed.when_to_seek_care_ko || "").trim()) errors.push("missing_when_to_seek_care_ko");
    if (parsed.evidence_bullets_ko != null && !Array.isArray(parsed.evidence_bullets_ko)) {
      errors.push("evidence_bullets_ko_not_array");
    }
    if (parsed.evidence_bullets_ko && parsed.evidence_bullets_ko.length > 5) {
      errors.push("evidence_bullets_ko_max_5");
    }
    if (parsed.seven_day_actions_ko != null) {
      if (!Array.isArray(parsed.seven_day_actions_ko)) errors.push("seven_day_actions_ko_not_array");
      else if (parsed.seven_day_actions_ko.length !== 7) errors.push("seven_day_actions_ko_expect_7");
    }
  }
  return { valid: errors.length === 0, errors };
}

const GUARD_ADVERSARIAL_REPLY_KO = [
  "본 서비스는 의료행위를 대체하지 않으며, 한의·양방의 확정 진단이나 한약 처방을 제공하지 않습니다.",
  "응급이 의심되면 즉시 119 또는 가까운 응급실로 가시기 바랍니다.",
  "안전을 위해 면책·한계 안내는 생략할 수 없습니다.",
].join("\n");

function textForRiskClassification({ question, context, messages }) {
  const parts = [String(question || ""), String(context || "")];
  if (Array.isArray(messages)) {
    for (const m of messages) {
      if (m && typeof m.content === "string") parts.push(m.content);
    }
  }
  return parts.join("\n");
}

/**
 * @returns {{ type: "normal" } | { type: "emergency" } | { type: "adversarial" }}
 */
function classifyChatRisk(raw) {
  const s = String(raw || "");
  if (!s.trim()) return { type: "normal" };
  const low = s.toLowerCase();
  const 면책생략 =
    (s.includes("면책") &&
      (s.includes("생략") ||
        s.includes("생략하") ||
        s.includes("빼고") ||
        s.includes("빼.") ||
        s.includes(" 빼 ") ||
        s.endsWith("빼") ||
        s.includes("제거") ||
        s.includes("없이"))) ||
    /without\s+disclaimer|remove\s+disclaimer/i.test(s);
  const 확정처방강요 = /(확정|단정|바로|즉시).*(처방|진단)|처방만|진단만/.test(s);
  const 의사역할 =
    /당신은\s*의사|너는\s*의사|의사니까|의사입니다|you\s+are\s+a\s+doctor/i.test(s) &&
    /처방|한약|진단/.test(s);
  if (면책생략 || 의사역할 || 확정처방강요) return { type: "adversarial" };

  const 응급 =
    (s.includes("가슴") && s.includes("왼팔")) ||
    /심근경색|뇌졸중|의식이\s*흐려|말이\s*어눌|119|응급실|heart\s+attack|stroke/i.test(low);
  if (응급) return { type: "emergency" };

  return { type: "normal" };
}

/** Remove common English chain-of-thought tails (Ollama models). */
function stripCoTLeakage(text) {
  if (!text || typeof text !== "string") return text;
  let out = text.replace(/<\/?(?:think|redacted_thinking)[^>]*>/gi, "");
  const cutPatterns = [
    /^\s*Okay,\s*(the user|let's|I need|I should|I must|we need)/im,
    /\n\s*Okay,\s*(the user|let's|I need|I should|I must|we need)/i,
    /^\s*Alright,\s*(so|let's)/im,
    /\n\s*Alright,\s*(so|let's)/i,
    /^\s*Let me\s+(start|think|begin|tackle)/im,
    /\n\s*Let me\s+(start|think|begin|tackle)/i,
    /^\s*Hmm,?\s*/im,
    /\n\s*Hmm,?\s*/i,
  ];
  for (const re of cutPatterns) {
    const idx = out.search(re);
    if (idx > 0) out = out.slice(0, idx);
  }
  // Leading English CoT line (no newline before "Okay")
  out = out
    .replace(/^\s*Okay,\s*the user[^\n]*/i, "")
    .replace(/^\s*Okay,\s*let's[^\n]*/i, "")
    .trim();
  return out;
}

/** Collapse 3+ consecutive identical non-empty lines (model repetition loops). */
function collapseRepeatedLines(text) {
  const lines = text.split("\n");
  const out = [];
  let lastKey = null;
  let dupStreak = 0;
  for (const line of lines) {
    const key = line.trim();
    if (key && key === lastKey) {
      dupStreak++;
      if (dupStreak >= 2) continue;
    } else {
      lastKey = key || null;
      dupStreak = 0;
    }
    out.push(line);
  }
  return out.join("\n").trim();
}

function applyAnswerGuards(answer) {
  let a = stripCoTLeakage(answer);
  a = collapseRepeatedLines(a);
  return a;
}

function normalizeFusionParsedShape(parsed) {
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return parsed;
  if (parsed.schema === "hanui_fusion_v2") return parsed;
  const mapped = {
    schema: "hanui_fusion_v2",
    summary_ko: String(parsed.summary_ko || parsed["요약"] || "").trim(),
    sasang_hypothesis:
      parsed.sasang_hypothesis ||
      ({
        constitution_ko: "",
        confidence: "low",
        rationale_ko: String(parsed["변증/감별 가설"] || "").slice(0, 300),
      }),
    myeongri_risk_tags: Array.isArray(parsed.myeongri_risk_tags) ? parsed.myeongri_risk_tags : [],
    neutralized_wisdom_actions: Array.isArray(parsed.neutralized_wisdom_actions)
      ? parsed.neutralized_wisdom_actions
      : [],
    drug_interaction_matrix: Array.isArray(parsed.drug_interaction_matrix)
      ? parsed.drug_interaction_matrix
      : [],
    differential_hypotheses: Array.isArray(parsed.differential_hypotheses) ? parsed.differential_hypotheses : [],
    evidence_citations: Array.isArray(parsed.evidence_citations)
      ? parsed.evidence_citations
      : Array.isArray(parsed.evidence_notes)
        ? parsed.evidence_notes
        : [],
    patient_plan_ko:
      parsed.patient_plan_ko ||
      ({
        daily: "",
        weekly: "",
        when_to_seek_care: String(parsed["다음 진료 액션"] || ""),
      }),
    limitations_ko: String(parsed.limitations_ko || parsed["근거·한계"] || "").trim(),
  };
  return mapped;
}

function enforceFusionMinimums(parsed, ctx) {
  const p = normalizeFusionParsedShape(parsed);
  const meds = Array.isArray(ctx?.medicationList) ? ctx.medicationList.filter(Boolean) : [];
  const sasang = String(ctx?.sasang_constitution || "").trim();
  const myeongri = String(ctx?.myeongri_notes || "").trim();
  const wisdomMode = String(ctx?.wisdomMode || "secular").toLowerCase();

  if (!p.summary_ko) p.summary_ko = "융합 렌즈 기반 보조 답변입니다. 최종 판단은 대면 진료에서 확정됩니다.";
  if (!p.sasang_hypothesis || typeof p.sasang_hypothesis !== "object") {
    p.sasang_hypothesis = { constitution_ko: sasang || "", confidence: "low", rationale_ko: "" };
  }
  if (!Array.isArray(p.myeongri_risk_tags)) p.myeongri_risk_tags = [];
  if (myeongri && p.myeongri_risk_tags.length === 0) {
    p.myeongri_risk_tags.push({ tag_ko: "명리 리스크 메모", rationale_ko: myeongri });
  }
  if (!Array.isArray(p.neutralized_wisdom_actions)) p.neutralized_wisdom_actions = [];
  if (p.neutralized_wisdom_actions.length === 0) {
    p.neutralized_wisdom_actions.push({
      theme_ko: "생활 리듬 안정",
      action_ko: "수면·식사·활동 루틴을 일정하게 유지하고 증상 변화를 기록합니다.",
      tone: wisdomMode === "secular" ? "secular" : "secular",
    });
  } else {
    p.neutralized_wisdom_actions = p.neutralized_wisdom_actions.map((x) => ({ ...x, tone: "secular" }));
  }

  if (!Array.isArray(p.drug_interaction_matrix)) p.drug_interaction_matrix = [];
  if (p.drug_interaction_matrix.length === 0 && meds.length > 0) {
    p.drug_interaction_matrix.push({
      drug_or_class: meds.join(", "),
      risk_note_ko: "복용약과 한의 상담 내용의 잠재 상호작용을 확인해야 합니다.",
      monitoring_ko: "복용 시간, 증상 변화, 혈압/맥박 및 이상반응을 추적 관찰합니다.",
    });
  }

  if (!Array.isArray(p.differential_hypotheses)) p.differential_hypotheses = [];
  if (!Array.isArray(p.evidence_citations)) p.evidence_citations = [];
  if (p.evidence_citations.length === 0) {
    p.evidence_citations.push({
      title: "RAG-lite internal guidance",
      summary_ko: "제공된 참고 스니펫을 바탕으로 안전 우선 원칙과 근거수준 표시를 적용합니다.",
      level: "요약",
    });
  }
  if (!p.patient_plan_ko || typeof p.patient_plan_ko !== "object") {
    p.patient_plan_ko = { daily: "", weekly: "", when_to_seek_care: "" };
  }
  p.patient_plan_ko.daily = String(p.patient_plan_ko.daily || "일일 증상·복약·수면 기록을 유지합니다.");
  p.patient_plan_ko.weekly = String(p.patient_plan_ko.weekly || "주 1회 변화 추세를 점검합니다.");
  p.patient_plan_ko.when_to_seek_care = String(
    p.patient_plan_ko.when_to_seek_care || "악화·응급 징후 시 즉시 응급실 또는 주치의 진료를 받습니다."
  );
  p.limitations_ko = String(
    p.limitations_ko || "본 출력은 보조 정보이며 확정 진단·처방을 대체하지 않습니다."
  );
  p.schema = "hanui_fusion_v2";
  return p;
}

function enforceClinicalMinimums(parsed) {
  const p = parsed && typeof parsed === "object" ? { ...parsed } : {};
  p.schema = "hanui_clinical_v1";
  p.summary_ko = String(p.summary_ko || "임상 보조 답변입니다. 최종 판단은 대면 진료에서 확정됩니다.");
  if (!Array.isArray(p.differential_hypotheses)) p.differential_hypotheses = [];
  if (!Array.isArray(p.red_flags_ko)) p.red_flags_ko = [];
  if (!Array.isArray(p.interaction_checks_ko)) p.interaction_checks_ko = [];
  if (!Array.isArray(p.evidence_notes)) p.evidence_notes = [];
  if (p.differential_hypotheses.length === 0) {
    p.differential_hypotheses.push({
      pattern_ko: "증상군 기반 가설",
      rationale_ko: "불면·불안·소화 증상 클러스터를 우선 문진하여 위험도와 패턴을 구분합니다.",
      distinguishing_questions: [
        "증상 악화 시간대(야간/식후/스트레스 직후)는 언제인가요?",
        "현재 복용약 또는 최근 복용 변경이 있었나요?",
        "흉통·호흡곤란·신경학적 이상 같은 응급 징후가 있나요?",
      ],
    });
  }
  p.differential_hypotheses = p.differential_hypotheses.map((h) => ({
    pattern_ko: String(h?.pattern_ko || "증상군 기반 가설"),
    rationale_ko: String(h?.rationale_ko || "핵심 증상과 위험 신호를 우선 확인합니다."),
    distinguishing_questions: Array.isArray(h?.distinguishing_questions)
      ? h.distinguishing_questions.filter(Boolean).map((q) => String(q))
      : [],
  }));
  if (p.evidence_notes.length === 0) {
    p.evidence_notes.push({
      note_ko: "응급 징후 배제 및 대면 진료 기반 확증이 필요합니다.",
      level: "요약",
    });
  }
  if (!p.patient_education_ko) p.patient_education_ko = "증상 악화 시 즉시 의료진과 상담하세요.";
  if (!Array.isArray(p.next_steps_ko)) p.next_steps_ko = ["48~72시간 경과 관찰 후 변화 재평가"];
  p.limitations_ko = String(p.limitations_ko || "본 출력은 보조 정보이며 확정 진단·처방을 대체하지 않습니다.");
  return p;
}

function enforceMkmlifeConsumerMinimums(parsed) {
  const p = parsed && typeof parsed === "object" ? { ...parsed } : {};
  p.schema = "mkmlife_consumer_v1";
  p.summary_ko = String(
    p.summary_ko || "모델 출력(JSON) 파싱 실패로 요약만 안전 재구성했습니다. 대면 진료로 확정이 필요합니다."
  ).trim();
  p.caution_ko = String(p.caution_ko || "AI 한계·면책: 확정 진단·한약 처방 정보가 아닙니다.").trim();
  p.when_to_seek_care_ko = String(
    p.when_to_seek_care_ko ||
      "가슴 통증·호흡곤란·의식 변화·심한 두통 등 응급 신호 시 즉시 119 또는 응급실을 이용하세요."
  ).trim();
  return p;
}

/** Strip ```json ... ``` fences if present. */
function stripMarkdownJsonFence(text) {
  if (!text || typeof text !== "string") return "";
  let t = text.trim();
  const fenced = t.match(/^```(?:json)?\s*\r?\n?([\s\S]*?)\r?\n?```\s*$/im);
  if (fenced) return fenced[1].trim();
  return t;
}

/**
 * Extract first top-level JSON object `{...}` with string-aware brace matching.
 * @returns {{ ok: true, value: object } | { ok: false, error: string }}
 */
function extractFirstJSONObject(text) {
  const cleaned = stripMarkdownJsonFence(text);
  const trimmed = cleaned.trim();
  if (trimmed.startsWith("{")) {
    try {
      const v = JSON.parse(trimmed);
      if (v !== null && typeof v === "object" && !Array.isArray(v)) return { ok: true, value: v };
    } catch {
      /* fall through to scan */
    }
  }
  const i = cleaned.indexOf("{");
  if (i === -1) return { ok: false, error: "no_json_object_start" };
  let depth = 0;
  let inStr = false;
  let esc = false;
  for (let j = i; j < cleaned.length; j++) {
    const c = cleaned[j];
    if (inStr) {
      if (esc) esc = false;
      else if (c === "\\") esc = true;
      else if (c === '"') inStr = false;
      continue;
    }
    if (c === '"') {
      inStr = true;
      continue;
    }
    if (c === "{") depth++;
    if (c === "}") {
      depth--;
      if (depth === 0) {
        const jsonStr = cleaned.slice(i, j + 1);
        try {
          const v = JSON.parse(jsonStr);
          if (v !== null && typeof v === "object" && !Array.isArray(v)) return { ok: true, value: v };
          return { ok: false, error: "root_not_object" };
        } catch (e) {
          return { ok: false, error: e.message || "json_parse_error" };
        }
      }
    }
  }
  return { ok: false, error: "unclosed_braces" };
}

const dataDir = path.join(process.cwd(), "data");
const paymentsFile = path.join(dataDir, "payapp_payments.json");
const verificationsFile = path.join(dataDir, "clinic_verifications.json");

app.use(express.json());
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type,Authorization");
  if (req.method === "OPTIONS") return res.status(204).end();
  next();
});

async function ensureDir() {
  await fs.mkdir(dataDir, { recursive: true });
}

async function readJson(filePath, fallback) {
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

async function writeJson(filePath, data) {
  await ensureDir();
  await fs.writeFile(filePath, JSON.stringify(data, null, 2), "utf-8");
}

function nowIso() {
  return new Date().toISOString();
}

function newRequestId() {
  return `req_${Date.now()}_${crypto.randomBytes(4).toString("hex")}`;
}

/**
 * Outgoing body for POST N8N_WEBHOOK_URL (Webhook node → your workflow).
 * n8n "Respond to Webhook" should return JSON with at least one of: answer | output | response | text
 */
function buildN8nWebhookPayload({
  question,
  category,
  context,
  messages,
  model,
  requestId,
  output_format,
  site_profile,
  reference_snippets,
}) {
  const rid = requestId || newRequestId();
  return {
    schema_version: N8N_CONTRACT_VERSION,
    event: "hanui_chat",
    question: question ?? "",
    category: category ?? "general",
    context: context ?? "",
    site_profile: site_profile ?? "no1kmedi",
    reference_snippets: reference_snippets ?? "",
    messages: Array.isArray(messages) ? messages : [],
    model: model ?? null,
    meta: {
      source: "no1kmedi-api",
      request_id: rid,
      timestamp: nowIso(),
      output_format: output_format || "text",
      site_profile: site_profile ?? "no1kmedi",
    },
  };
}

function pickString(...candidates) {
  for (const c of candidates) {
    if (typeof c === "string" && c.trim()) return c.trim();
  }
  return "";
}

/**
 * Normalize n8n / LLM passthrough / plain-text responses.
 */
function extractAnswerFromN8nJson(data) {
  if (data == null) return "";
  if (typeof data === "string") return data.trim();

  const direct = pickString(
    data.answer,
    data.output,
    data.response,
    data.text,
    data.message,
    data.result,
    data.content,
    data?.data?.answer,
    data?.data?.output,
    data?.data?.text,
    data?.result?.answer,
    data?.body?.answer,
    data?.json?.answer,
    data?.json?.output,
    data?.json?.text
  );
  if (direct) return direct;

  const choice = data?.choices?.[0]?.message?.content;
  if (typeof choice === "string" && choice.trim()) return choice.trim();

  if (Array.isArray(data)) {
    for (const row of data) {
      const t = extractAnswerFromN8nJson(row);
      if (t) return t;
    }
  }

  return "";
}

async function parseN8nResponse(res) {
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  const rawText = await res.text();
  if (!rawText.trim()) return "";

  if (ct.includes("application/json") || rawText.trim().startsWith("{") || rawText.trim().startsWith("[")) {
    try {
      const data = JSON.parse(rawText);
      return extractAnswerFromN8nJson(data);
    } catch {
      return rawText.trim();
    }
  }
  return rawText.trim();
}

function normalizeState(rawState) {
  const v = String(rawState || "").toLowerCase();
  if (["paid", "success", "done", "completed", "결제완료"].includes(v)) return "paid";
  if (["failed", "cancel", "error", "취소", "실패"].includes(v)) return "failed";
  return "pending";
}

async function callOpenRouter(messages, model) {
  if (!OPENROUTER_API_KEY) throw new Error("OPENROUTER_API_KEY is not configured");
  const res = await fetchWithTimeout(
    "https://openrouter.ai/api/v1/chat/completions",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${OPENROUTER_API_KEY}`,
      },
      body: JSON.stringify({
        model: model || OPENROUTER_MODEL,
        messages,
        temperature: 0.3,
      }),
    },
    OPENROUTER_FETCH_TIMEOUT_MS
  );
  if (!res.ok) throw new Error(`OpenRouter error: ${res.status}`);
  const data = await res.json();
  return data?.choices?.[0]?.message?.content || "";
}

async function callLocalModel(messages, model) {
  if (!LOCAL_LLM_URL) throw new Error("LOCAL_LLM_URL or OLLAMA_HOST is not configured");
  const res = await fetchWithTimeout(
    LOCAL_LLM_URL,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: model || LOCAL_LLM_DEFAULT_MODEL,
        messages,
        temperature: 0.3,
      }),
    },
    LOCAL_LLM_FETCH_TIMEOUT_MS
  );
  if (!res.ok) throw new Error(`Local model error: ${res.status}`);
  const data = await res.json();
  return data?.choices?.[0]?.message?.content || data?.response || "";
}

async function callN8n({
  question,
  category,
  context,
  messages,
  model,
  requestId,
  output_format,
  site_profile,
  reference_snippets,
}) {
  if (!N8N_WEBHOOK_URL) throw new Error("N8N_WEBHOOK_URL is not configured");
  const payload = buildN8nWebhookPayload({
    question,
    category,
    context,
    messages,
    model,
    requestId,
    output_format,
    site_profile,
    reference_snippets,
  });
  const res = await fetchWithTimeout(
    N8N_WEBHOOK_URL,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/plain;q=0.9,*/*;q=0.8",
      },
      body: JSON.stringify(payload),
    },
    N8N_FETCH_TIMEOUT_MS
  );
  if (!res.ok) {
    const errBody = await res.text().catch(() => "");
    throw new Error(`n8n webhook error: ${res.status} ${errBody.slice(0, 200)}`);
  }
  const answer = await parseN8nResponse(res);
  if (!answer) {
    throw new Error(
      "n8n returned empty body or missing answer field (use Respond to Webhook JSON: { \"answer\": \"...\" } or plain text)"
    );
  }
  return answer;
}

async function retryJsonResponseWithProvider({
  provider,
  safeMessages,
  model,
  openrouterModel,
  localModel,
  question,
  category,
  context,
  request_id,
  output_format,
  site_profile,
  reference_snippets,
  reason,
}) {
  const retryInstruction = {
    role: "system",
    content:
      "[RETRY_JSON_ENFORCE] Previous output failed JSON/contract checks. Return ONE strict JSON object only, exact schema keys only, no prose.",
  };
  const retryMessages = [...safeMessages, retryInstruction];
  if (provider === "n8n") {
    return callN8n({
      question,
      category,
      context,
      messages: retryMessages,
      model,
      requestId: request_id,
      output_format,
      site_profile,
      reference_snippets: `${reference_snippets || ""}\n[retry_reason] ${reason || "json_contract_retry"}`.trim(),
    });
  }
  if (provider === "openrouter") return callOpenRouter(retryMessages, openrouterModel || model);
  if (provider === "local") return callLocalModel(retryMessages, localModel || model);
  return "";
}

app.get("/health", (_req, res) => {
  res.json({
    ok: true,
    service: "no1kmedi-payapp-api",
    gateway: {
      site_profiles: ["mkmlife", "no1kmedi"],
      json_schemas: ["hanui_clinical_v1", "hanui_fusion_v2", "mkmlife_consumer_v1"],
    },
  });
});

app.get("/api/ai/router-status", (_req, res) => {
  const localConfigured = !!LOCAL_LLM_URL;
  const n8nConfigured = !!N8N_WEBHOOK_URL;
  const openrouterConfigured = !!OPENROUTER_API_KEY;
  const urlFromOllamaHost = !String(process.env.LOCAL_LLM_URL || "").trim() && !!String(process.env.OLLAMA_HOST || "").trim();
  res.json({
    success: true,
    ai_router_mode: AI_ROUTER_MODE,
    ai_chat_guards: AI_CHAT_GUARDS,
    has_backend: hasAiBackendConfigured(),
    backends: {
      n8n: n8nConfigured,
      local: localConfigured,
      openrouter: openrouterConfigured,
    },
    local_llm_url: localConfigured ? LOCAL_LLM_URL : null,
    local_llm_url_derived_from_ollama_host: urlFromOllamaHost,
    local_llm_default_model: LOCAL_LLM_DEFAULT_MODEL,
    fetch_timeouts_ms: {
      n8n: N8N_FETCH_TIMEOUT_MS,
      openrouter: OPENROUTER_FETCH_TIMEOUT_MS,
      local_llm: LOCAL_LLM_FETCH_TIMEOUT_MS,
    },
    mkmlife_overrides: {
      MKMLIFE_AI_ROUTER_MODE: String(process.env.MKMLIFE_AI_ROUTER_MODE || "").trim() || null,
      MKMLIFE_OPENROUTER_MODEL: String(process.env.MKMLIFE_OPENROUTER_MODEL || "").trim() || null,
      MKMLIFE_LOCAL_LLM_MODEL: String(process.env.MKMLIFE_LOCAL_LLM_MODEL || "").trim() || null,
    },
  });
});

app.get("/api/ai/n8n-contract", (_req, res) => {
  res.json({
    schema_version: N8N_CONTRACT_VERSION,
    description:
      "Gateway POSTs this JSON to N8N_WEBHOOK_URL. n8n should end with Respond to Webhook returning JSON { answer } or plain text.",
    request_to_n8n: {
      method: "POST",
      content_type: "application/json",
      fields: {
        schema_version: `fixed string "${N8N_CONTRACT_VERSION}"`,
        event: "hanui_chat",
        question: "user question (string)",
        category: "e.g. general | emergency | herb (string)",
        context: "RAG or extra context (string)",
        site_profile: "mkmlife | no1kmedi (optional; aliases: profile, mkmlife.com)",
        reference_snippets: "server-side RAG hits (auto; also sent for operator visibility)",
        messages: "OpenAI-style [{ role, content }, ...]",
        model: "optional model id (string|null)",
        meta: {
          source: "no1kmedi-api",
          request_id: "correlation id",
          timestamp: "ISO-8601",
          site_profile: "mkmlife | no1kmedi",
        },
      },
    },
    response_from_n8n: {
      preferred: { answer: "final assistant text (string)" },
      also_parsed: [
        "output",
        "response",
        "text",
        "json.answer / json.output (n8n item wrapper)",
        "data.answer",
        "choices[0].message.content",
        "raw text body",
      ],
    },
    gateway: {
      chat_url: "POST /api/ai/chat",
      optional_body_fields: [
        "request_id — forwarded as meta.request_id if set; else auto-generated",
        "site_profile | profile — mkmlife (public) vs no1kmedi (clinician); drives system prompt + default json_schema",
        "json_schema — when output_format=json: hanui_clinical_v1 | hanui_fusion_v2 | mkmlife_consumer_v1 (defaults by profile)",
        "sasang_constitution / myeongri_notes / medications — optional fusion lens inputs",
        "wisdom_mode=secular — transform wisdom/spiritual lens to non-religious self-management actions",
        "output_format — text (default) | json — json adds schema-specific hint; see response.output",
      ],
      response_output: {
        format: "text | json",
        json_valid: "boolean when output_format was json",
        parsed: "object when json_valid true",
        json_error: "string when json_valid false",
      },
    },
    env: {
      N8N_WEBHOOK_URL: "Webhook URL from n8n (Production URL)",
      AI_ROUTER_MODE: "hybrid (default) | n8n | openrouter | local",
      AI_CHAT_GUARDS: "1 (default) — adversarial short-circuit + emergency system hint + CoT strip; set 0 to disable",
      N8N_FETCH_TIMEOUT_MS: "n8n fetch timeout (default 12000); AbortError triggers hybrid failover",
      OPENROUTER_FETCH_TIMEOUT_MS: "OpenRouter fetch timeout (default 60000)",
      LOCAL_LLM_TIMEOUT_MS: "Local OpenAI-compatible fetch timeout (default 120000); alias LOCAL_LLM_FETCH_TIMEOUT_MS",
      MKMLIFE_AI_ROUTER_MODE: "Optional: when site_profile=mkmlife, override AI_ROUTER_MODE (same enum)",
      MKMLIFE_OPENROUTER_MODEL: "Optional: default OpenRouter model id for mkmlife when request model omitted",
      MKMLIFE_LOCAL_LLM_MODEL: "Optional: default local model id for mkmlife when request model omitted",
    },
  });
});

app.post("/api/ai/chat", async (req, res) => {
  try {
    const {
      question,
      category,
      context,
      messages,
      model,
      request_id,
      output_format: rawOutputFormat,
      json_schema: rawJsonSchema,
      site_profile: rawSiteProfile,
      profile: profileAlias,
      sasang_constitution,
      myeongri_notes,
      medications,
      wisdom_mode,
    } = req.body || {};

    const site_profile = normalizeSiteProfile(rawSiteProfile ?? profileAlias);
    const output_format = String(rawOutputFormat || "text").toLowerCase() === "json" ? "json" : "text";
    const jsonSchema = resolveJsonSchema(site_profile, output_format, rawJsonSchema);
    const jsonFmt = output_format === "json" ? jsonSchemaHint(jsonSchema) : "";
    const medicationList = Array.isArray(medications) ? medications : [];
    const medicationText = medicationList.filter(Boolean).join(", ");
    const wisdomMode = String(wisdom_mode || "secular").toLowerCase();

    let fusionExtra = "";
    if (jsonSchema === "hanui_fusion_v2") {
      fusionExtra = [
        "\n[FUSION_INPUT]",
        `- sasang_constitution: ${sasang_constitution || "(미입력)"}`,
        `- myeongri_notes: ${myeongri_notes || "(미입력)"}`,
        `- medications: ${medicationText || "(미입력)"}`,
        `- wisdom_mode: ${wisdomMode}`,
        "",
        "[FUSION_RULES]",
        "- 사상/명리는 가설 렌즈로만 제시하고 확정 진단처럼 단정하지 말 것.",
        "- spiritual/scripture 렌즈가 포함되어도 출력은 종교색 없이 secular 행동지침으로 변환할 것.",
        "- 복용약이 있으면 drug_interaction_matrix를 비우지 말고 모니터링 항목을 포함할 것.",
      ].join("\n");
    }

    const risk = classifyChatRisk(textForRiskClassification({ question, context, messages }));
    const guardMeta = { risk: risk.type, strips: [] };

    if (AI_CHAT_GUARDS && risk.type === "adversarial") {
      const outputMeta = { format: output_format, skipped_llm: true, json_schema: jsonSchema };
      if (output_format === "json") {
        outputMeta.json_valid = false;
        outputMeta.json_error = "guard_refusal_plain_text";
      }
      return res.json({
        success: true,
        provider: "guard",
        site_profile,
        answer: GUARD_ADVERSARIAL_REPLY_KO,
        guard: { ...guardMeta, applied: ["adversarial_refusal"] },
        output: outputMeta,
        rag: { hits: [] },
        ai_trace: {
          router_mode: effectiveAiRouterMode(site_profile),
          site_profile,
          router_trace: ["guard:adversarial_refusal"],
          model_used: null,
          ai_provider: "guard",
          ai_router_mode_default: AI_ROUTER_MODE,
        },
      });
    }

    if (!hasAiBackendConfigured()) {
      return res.status(503).json({
        success: false,
        error: "ai_backend_unconfigured",
        ai_router_mode: AI_ROUTER_MODE,
        ai_router_mode_effective: effectiveAiRouterMode(site_profile),
        site_profile,
        hint:
          "Set at least one of N8N_WEBHOOK_URL, LOCAL_LLM_URL (OpenAI-compatible /v1/chat/completions), or OPENROUTER_API_KEY on this server.",
      });
    }

    const rag = await retrieveHanuiRagLite(question, 3);
    const reference_snippets = rag.text || "";

    let systemExtra = "";
    if (AI_CHAT_GUARDS && risk.type === "emergency") {
      systemExtra =
        "\n[URGENT] User text may describe an emergency. Prioritize 119/ER. Do not give herbal prescriptions. Korean answer.";
    }

    const baseSystem = systemPromptForProfile(site_profile);
    const ragBlock = reference_snippets ? `\n[참고_snippets_RAG_lite]\n${reference_snippets}` : "";
    const fusionBlock = fusionExtra ? `\n${fusionExtra}` : "";

    let safeMessages;
    if (Array.isArray(messages) && messages.length > 0) {
      if (messages[0]?.role === "system") {
        safeMessages = messages.map((m, i) =>
          i === 0
            ? { ...m, content: `${baseSystem}\n${m.content}${ragBlock}${fusionBlock}${systemExtra}${jsonFmt}` }
            : m
        );
      } else {
        safeMessages = [
          { role: "system", content: `${baseSystem}${ragBlock}${fusionBlock}${systemExtra}${jsonFmt}` },
          ...messages,
        ];
      }
    } else {
      safeMessages = [
        { role: "system", content: `${baseSystem}${ragBlock}${fusionBlock}${systemExtra}${jsonFmt}` },
        {
          role: "user",
          content: `category:${category || "general"}\nquestion:${question || ""}\nreference_snippets:\n${reference_snippets || "(없음)"}\nadditional_context:\n${context || ""}\nsasang_constitution:${sasang_constitution || ""}\nmyeongri_notes:${myeongri_notes || ""}\nmedications:${medicationText || ""}\nwisdom_mode:${wisdomMode}`,
        },
      ];
    }

    const mode = effectiveAiRouterMode(site_profile);
    const router_trace = [];
    const orModel = pickModelForBackend(site_profile, model, "openrouter") || OPENROUTER_MODEL;
    const locModel = pickModelForBackend(site_profile, model, "local") || LOCAL_LLM_DEFAULT_MODEL;

    let answer = "";
    let provider = "none";

    const n8nArgs = () => ({
      question,
      category,
      context,
      messages: safeMessages,
      model,
      requestId: request_id,
      output_format,
      site_profile,
      reference_snippets,
    });

    if (mode === "n8n") {
      router_trace.push("route:n8n_only");
      try {
        answer = await callN8n(n8nArgs());
        provider = "n8n";
        router_trace.push("n8n:ok");
      } catch (e) {
        router_trace.push(e?.name === "AbortError" ? "n8n:timeout" : `n8n:err:${slugRouterError(e)}`);
        throw e;
      }
    } else if (mode === "openrouter") {
      router_trace.push("route:openrouter_only");
      answer = await callOpenRouter(safeMessages, orModel);
      provider = "openrouter";
      router_trace.push("openrouter:ok");
    } else if (mode === "local") {
      router_trace.push("route:local_only");
      answer = await callLocalModel(safeMessages, locModel);
      provider = "local";
      router_trace.push("local:ok");
    } else {
      // hybrid: n8n -> local -> openrouter (never call OpenRouter without a key)
      router_trace.push("route:hybrid");
      try {
        router_trace.push("n8n:start");
        answer = await callN8n(n8nArgs());
        provider = "n8n";
        router_trace.push("n8n:ok");
      } catch (e) {
        router_trace.push(e?.name === "AbortError" ? "n8n:timeout" : `n8n:err:${slugRouterError(e)}`);
        try {
          router_trace.push("local:start");
          answer = await callLocalModel(safeMessages, locModel);
          provider = "local";
          router_trace.push("local:ok");
        } catch (e2) {
          router_trace.push(`local:err:${slugRouterError(e2)}`);
          if (!OPENROUTER_API_KEY) {
            return res.status(503).json({
              success: false,
              error: "ai_backend_unconfigured",
              ai_router_mode: "hybrid",
              ai_router_mode_effective: mode,
              site_profile,
              router_trace,
              hint:
                "n8n/local failed or were not configured. Set OPENROUTER_API_KEY, or fix N8N_WEBHOOK_URL / LOCAL_LLM_URL.",
            });
          }
          router_trace.push("openrouter:start");
          answer = await callOpenRouter(safeMessages, orModel);
          provider = "openrouter";
          router_trace.push("openrouter:ok");
        }
      }
    }

    if (AI_CHAT_GUARDS && answer) {
      const before = answer.length;
      answer = applyAnswerGuards(answer);
      if (answer.length < before) guardMeta.strips.push("cot_or_repeat");
    }

    const outputMeta = { format: output_format, json_schema: jsonSchema };
    if (output_format === "json") {
      const parseAndValidate = (rawAnswer) => {
        if (!rawAnswer || !String(rawAnswer).trim()) {
          return { json_valid: false, json_error: "empty_answer", parsed: null, contract_valid: false, contract_errors: [] };
        }
        const ex = extractFirstJSONObject(rawAnswer);
        if (!ex.ok) return { json_valid: false, json_error: ex.error, parsed: null, contract_valid: false, contract_errors: [] };
        let parsed = ex.value;
        if (jsonSchema === "hanui_fusion_v2") {
          parsed = enforceFusionMinimums(parsed, {
            medicationList,
            sasang_constitution,
            myeongri_notes,
            wisdomMode,
          });
        }
        const cv = jsonSchema ? validateJsonContract(parsed, jsonSchema) : { valid: true, errors: [] };
        return {
          json_valid: true,
          json_error: null,
          parsed,
          contract_valid: cv.valid,
          contract_errors: cv.errors,
        };
      };

      let judged = parseAndValidate(answer);
      if (
        provider !== "guard" &&
        (!judged.json_valid || (jsonSchema && judged.contract_valid === false))
      ) {
        const retried = await retryJsonResponseWithProvider({
          provider,
          safeMessages,
          model,
          openrouterModel: orModel,
          localModel: locModel,
          question,
          category,
          context,
          request_id,
          output_format,
          site_profile,
          reference_snippets,
          reason: judged.json_error || (judged.contract_errors || []).join(","),
        });
        if (retried && String(retried).trim()) {
          answer = retried;
          judged = parseAndValidate(answer);
          outputMeta.retry_applied = true;
        }
      }

      outputMeta.json_valid = judged.json_valid;
      if (!judged.json_valid) {
        if (jsonSchema === "hanui_fusion_v2") {
          const fallbackParsed = enforceFusionMinimums(
            {
              summary_ko: `모델 출력(JSON) 파싱 실패로 안전 폴백을 사용합니다. 원문 일부: ${String(answer || "").slice(0, 180)}`,
              evidence_citations: (rag?.hits || []).map((h) => ({
                title: `${h.id || "rag_hit"}|${h.source_label || "rag"}`,
                summary_ko: "RAG 스니펫 기반 안전 폴백 요약",
                level: "요약",
              })),
            },
            { medicationList, sasang_constitution, myeongri_notes, wisdomMode }
          );
          judged = {
            json_valid: true,
            json_error: null,
            parsed: fallbackParsed,
            contract_valid: true,
            contract_errors: [],
          };
          outputMeta.fallback_structured = true;
          outputMeta.retry_applied = outputMeta.retry_applied || false;
          outputMeta.fallback_reason = "json_parse_failed_after_retry";
          outputMeta.parsed = judged.parsed;
          outputMeta.contract_valid = true;
          outputMeta.contract_errors = [];
          answer = JSON.stringify(judged.parsed, null, 2);
          outputMeta.json_valid = true;
        } else if (jsonSchema === "hanui_clinical_v1") {
          const fallbackParsed = enforceClinicalMinimums({
            summary_ko: `모델 출력(JSON) 파싱 실패로 안전 폴백을 사용합니다. 원문 일부: ${String(answer || "").slice(0, 180)}`,
            evidence_notes: [
              {
                note_ko: "RAG-lite 및 안전 가드레일 기준으로 보수적 기본값을 적용했습니다.",
                level: "요약",
              },
            ],
          });
          judged = {
            json_valid: true,
            json_error: null,
            parsed: fallbackParsed,
            contract_valid: true,
            contract_errors: [],
          };
          outputMeta.fallback_structured = true;
          outputMeta.retry_applied = outputMeta.retry_applied || false;
          outputMeta.fallback_reason = "json_parse_failed_after_retry";
          outputMeta.parsed = judged.parsed;
          outputMeta.contract_valid = true;
          outputMeta.contract_errors = [];
          answer = JSON.stringify(judged.parsed, null, 2);
          outputMeta.json_valid = true;
        } else if (jsonSchema === "mkmlife_consumer_v1") {
          const fallbackParsed = enforceMkmlifeConsumerMinimums({
            summary_ko: `모델 출력(JSON) 파싱 실패로 안전 폴백을 사용합니다. 원문 일부: ${String(answer || "").slice(0, 180)}`,
          });
          judged = {
            json_valid: true,
            json_error: null,
            parsed: fallbackParsed,
            contract_valid: true,
            contract_errors: [],
          };
          outputMeta.fallback_structured = true;
          outputMeta.retry_applied = outputMeta.retry_applied || false;
          outputMeta.fallback_reason = "json_parse_failed_after_retry";
          outputMeta.parsed = judged.parsed;
          outputMeta.contract_valid = true;
          outputMeta.contract_errors = [];
          answer = JSON.stringify(judged.parsed, null, 2);
          outputMeta.json_valid = true;
        } else {
          outputMeta.json_error = judged.json_error;
          outputMeta.raw_excerpt = String(answer || "").slice(0, 600);
        }
      } else {
        outputMeta.parsed = judged.parsed;
        outputMeta.contract_valid = judged.contract_valid;
        outputMeta.contract_errors = judged.contract_errors;
        answer = JSON.stringify(judged.parsed, null, 2);
      }
    }

    const model_used =
      provider === "openrouter"
        ? orModel
        : provider === "local"
          ? locModel
          : provider === "n8n"
            ? (model && String(model).trim()) || null
            : null;

    const payload = {
      success: true,
      provider,
      site_profile,
      answer,
      guard: guardMeta,
      output: outputMeta,
      rag,
      ai_trace: {
        router_mode: mode,
        site_profile,
        router_trace,
        model_used,
        /** Composite for dashboards: "openrouter/openai/gpt-4o-mini" or "n8n" */
        ai_provider: model_used ? `${provider}/${model_used}` : provider,
        ai_router_mode_default: AI_ROUTER_MODE,
      },
    };
    if (provider === "n8n") payload.n8n_contract_version = N8N_CONTRACT_VERSION;
    return res.json(payload);
  } catch (error) {
    return res.status(500).json({ success: false, error: error.message || "ai chat failed" });
  }
});

app.post("/api/payment/payapp/create", async (req, res) => {
  try {
    const { payapp_key, payapp_value, email, plan_code, product_name, return_url, amount } = req.body || {};
    if (!payapp_key || !payapp_value || !email || !plan_code) {
      return res.status(400).json({ success: false, error: "payapp_key, payapp_value, email, plan_code are required." });
    }

    const orderId = `mkm_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    const rows = await readJson(paymentsFile, []);
    rows.unshift({
      order_id: orderId,
      email: String(email).toLowerCase(),
      plan_code,
      amount: Number(amount) || 39000,
      state: "pending",
      raw: { product_name, return_url },
      created_at: nowIso(),
      updated_at: nowIso()
    });
    await writeJson(paymentsFile, rows);

    const origin = `https://${req.get("host")}`;
    const redirectUrl = `https://api.payapp.kr/oapi/pay?mul_no=${encodeURIComponent(payapp_key)}&ordr_idxx=${encodeURIComponent(orderId)}&good_name=${encodeURIComponent(product_name || "MKM Hanui Clinical Assistant")}&good_mny=${encodeURIComponent(String(amount || 39000))}&feedbackurl=${encodeURIComponent(`${origin}/api/payment/payapp/feedback`)}&return_url=${encodeURIComponent(return_url || "https://no1kmedi.com")}`;

    return res.json({
      success: true,
      order_id: orderId,
      payment_status: "pending",
      redirect_url: redirectUrl
    });
  } catch (error) {
    return res.status(500).json({ success: false, error: error.message || "payapp create failed" });
  }
});

app.post("/api/payment/payapp/feedback", async (req, res) => {
  try {
    const payload = req.body || {};
    const orderId = payload.order_id || payload.ordr_idxx || payload.orderId;
    if (!orderId) return res.status(400).json({ success: false, error: "order_id missing" });

    const rows = await readJson(paymentsFile, []);
    const idx = rows.findIndex((x) => x.order_id === orderId);
    const state = normalizeState(payload.state || payload.status || payload.pay_status);
    if (idx >= 0) {
      rows[idx] = { ...rows[idx], state, raw: payload, updated_at: nowIso() };
    } else {
      rows.unshift({
        order_id: orderId,
        email: String(payload.email || "unknown").toLowerCase(),
        plan_code: payload.plan_code || "unknown",
        amount: Number(payload.amount) || 0,
        state,
        raw: payload,
        created_at: nowIso(),
        updated_at: nowIso()
      });
    }
    await writeJson(paymentsFile, rows);
    return res.json({ success: true });
  } catch (error) {
    return res.status(500).json({ success: false, error: error.message || "feedback handling failed" });
  }
});

app.get("/api/payment/payapp/status", async (req, res) => {
  try {
    const email = String(req.query.email || "").toLowerCase();
    const orderId = String(req.query.order_id || "");
    const rows = await readJson(paymentsFile, []);
    const target = rows.find((x) => (orderId ? x.order_id === orderId : email ? x.email === email : false));
    if (!target) return res.status(404).json({ success: false, error: "payment not found" });
    return res.json({
      success: true,
      order_id: target.order_id,
      email: target.email,
      plan_code: target.plan_code,
      payment_status: target.state,
      updated_at: target.updated_at
    });
  } catch (error) {
    return res.status(500).json({ success: false, error: error.message || "status lookup failed" });
  }
});

app.post("/api/member/verification/submit", async (req, res) => {
  try {
    const { email, clinic_name, biz_number, license_number, note } = req.body || {};
    if (!email || !clinic_name || !biz_number || !license_number) {
      return res.status(400).json({ success: false, error: "email, clinic_name, biz_number, license_number are required." });
    }
    const rows = await readJson(verificationsFile, []);
    const id = `verify_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    rows.unshift({
      id,
      email: String(email).toLowerCase(),
      clinic_name,
      biz_number,
      license_number,
      note,
      status: "pending",
      created_at: nowIso(),
      updated_at: nowIso()
    });
    await writeJson(verificationsFile, rows);
    return res.json({ success: true, verification_id: id, verification_status: "pending" });
  } catch (error) {
    return res.status(500).json({ success: false, error: error.message || "verification submit failed" });
  }
});

app.post("/api/member/verification/review", async (req, res) => {
  try {
    const { verification_id, decision, admin_token, reviewer } = req.body || {};
    if (!verification_id || !decision) {
      return res.status(400).json({ success: false, error: "verification_id and decision are required." });
    }
    if (admin_token !== ADMIN_TOKEN) {
      return res.status(401).json({ success: false, error: "unauthorized" });
    }
    if (!["approved", "rejected"].includes(decision)) {
      return res.status(400).json({ success: false, error: "decision must be approved or rejected" });
    }
    const rows = await readJson(verificationsFile, []);
    const idx = rows.findIndex((x) => x.id === verification_id);
    if (idx < 0) return res.status(404).json({ success: false, error: "verification not found" });
    rows[idx] = { ...rows[idx], status: decision, reviewed_by: reviewer || "admin", updated_at: nowIso() };
    await writeJson(verificationsFile, rows);
    return res.json({ success: true, verification_id, verification_status: rows[idx].status });
  } catch (error) {
    return res.status(500).json({ success: false, error: error.message || "verification review failed" });
  }
});

app.get("/api/member/access-status", async (req, res) => {
  try {
    const email = String(req.query.email || "").toLowerCase();
    if (!email) return res.status(400).json({ success: false, error: "email is required" });
    const [payments, verifications] = await Promise.all([
      readJson(paymentsFile, []),
      readJson(verificationsFile, [])
    ]);
    const payment = payments.find((x) => x.email === email);
    const verification = verifications.find((x) => x.email === email);
    const paymentStatus = payment?.state || "none";
    const verificationStatus = verification?.status || "not_submitted";
    const unlocked = paymentStatus === "paid" && verificationStatus === "approved";
    return res.json({
      success: true,
      email,
      payment_status: paymentStatus,
      verification_status: verificationStatus,
      can_use_pro_clinical_assist: unlocked,
      pro_clinical_features_unlocked: unlocked,
    });
  } catch (error) {
    return res.status(500).json({ success: false, error: error.message || "access status failed" });
  }
});

app.listen(PORT, () => {
  console.log(`no1kmedi-payapp-api listening on :${PORT}`);
});
