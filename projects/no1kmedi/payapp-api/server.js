import express from "express";
import fs from "fs/promises";
import path from "path";
import crypto from "crypto";

const app = express();
const PORT = process.env.PORT || 3000;
const ADMIN_TOKEN = process.env.NO1KMEDI_ADMIN_TOKEN || "NO1KMEDI_2026_xF7pQ2mL9vR4kT8sW1dH6nC3bY5uJ0aZ";
const N8N_WEBHOOK_URL = process.env.N8N_WEBHOOK_URL || "";
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || "";
const OPENROUTER_MODEL = process.env.OPENROUTER_MODEL || "openai/gpt-4.1-mini";
const LOCAL_LLM_URL = process.env.LOCAL_LLM_URL || ""; // ex: http://127.0.0.1:11434/v1/chat/completions
const AI_ROUTER_MODE = (process.env.AI_ROUTER_MODE || "hybrid").toLowerCase(); // n8n|openrouter|local|hybrid
/** Set AI_CHAT_GUARDS=0 to disable adversarial block + CoT stripping (debug only). */
const AI_CHAT_GUARDS = process.env.AI_CHAT_GUARDS !== "0";

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
  const 면책생략 = s.includes("면책") && (s.includes("생략") || s.includes("생략하"));
  const 의사역할 =
    /당신은\s*의사|의사입니다|you\s+are\s+a\s+doctor/i.test(s) && /처방|한약/.test(s);
  if (면책생략 || 의사역할) return { type: "adversarial" };

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

const JSON_OUTPUT_HINT =
  "\n[OUTPUT] Respond with a single JSON object only. No markdown fences, no explanatory text before or after the JSON.";

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
function buildN8nWebhookPayload({ question, category, context, messages, model, requestId, output_format }) {
  const rid = requestId || newRequestId();
  return {
    schema_version: N8N_CONTRACT_VERSION,
    event: "hanui_chat",
    question: question ?? "",
    category: category ?? "general",
    context: context ?? "",
    messages: Array.isArray(messages) ? messages : [],
    model: model ?? null,
    meta: {
      source: "no1kmedi-api",
      request_id: rid,
      timestamp: nowIso(),
      output_format: output_format || "text",
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
  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
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
  });
  if (!res.ok) throw new Error(`OpenRouter error: ${res.status}`);
  const data = await res.json();
  return data?.choices?.[0]?.message?.content || "";
}

async function callLocalModel(messages, model) {
  if (!LOCAL_LLM_URL) throw new Error("LOCAL_LLM_URL is not configured");
  const res = await fetch(LOCAL_LLM_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, messages, temperature: 0.3 }),
  });
  if (!res.ok) throw new Error(`Local model error: ${res.status}`);
  const data = await res.json();
  return data?.choices?.[0]?.message?.content || data?.response || "";
}

async function callN8n({ question, category, context, messages, model, requestId, output_format }) {
  if (!N8N_WEBHOOK_URL) throw new Error("N8N_WEBHOOK_URL is not configured");
  const payload = buildN8nWebhookPayload({ question, category, context, messages, model, requestId, output_format });
  const res = await fetch(N8N_WEBHOOK_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json, text/plain;q=0.9,*/*;q=0.8",
    },
    body: JSON.stringify(payload),
  });
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

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "no1kmedi-payapp-api" });
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
        messages: "OpenAI-style [{ role, content }, ...]",
        model: "optional model id (string|null)",
        meta: { source: "no1kmedi-api", request_id: "correlation id", timestamp: "ISO-8601" },
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
        "output_format — text (default) | json — json adds system JSON-only hint, parses first {...} in reply; see response.output",
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
    },
  });
});

app.post("/api/ai/chat", async (req, res) => {
  try {
    const { question, category, context, messages, model, request_id, output_format: rawOutputFormat } = req.body || {};
    const output_format = String(rawOutputFormat || "text").toLowerCase() === "json" ? "json" : "text";
    const jsonFmt = output_format === "json" ? JSON_OUTPUT_HINT : "";

    const risk = classifyChatRisk(textForRiskClassification({ question, context, messages }));
    const guardMeta = { risk: risk.type, strips: [] };

    if (AI_CHAT_GUARDS && risk.type === "adversarial") {
      const outputMeta = { format: output_format, skipped_llm: true };
      if (output_format === "json") {
        outputMeta.json_valid = false;
        outputMeta.json_error = "guard_refusal_plain_text";
      }
      return res.json({
        success: true,
        provider: "guard",
        answer: GUARD_ADVERSARIAL_REPLY_KO,
        guard: { ...guardMeta, applied: ["adversarial_refusal"] },
        output: outputMeta,
      });
    }

    if (!hasAiBackendConfigured()) {
      return res.status(503).json({
        success: false,
        error: "ai_backend_unconfigured",
        ai_router_mode: AI_ROUTER_MODE,
        hint:
          "Set at least one of N8N_WEBHOOK_URL, LOCAL_LLM_URL (OpenAI-compatible /v1/chat/completions), or OPENROUTER_API_KEY on this server.",
      });
    }

    let systemExtra = "";
    if (AI_CHAT_GUARDS && risk.type === "emergency") {
      systemExtra =
        "\n[URGENT] User text may describe an emergency. Prioritize 119/ER. Do not give herbal prescriptions. Korean answer.";
    }

    let safeMessages;
    if (Array.isArray(messages) && messages.length > 0) {
      if (messages[0]?.role === "system") {
        safeMessages = messages.map((m, i) =>
          i === 0 ? { ...m, content: `${HANUI_SYSTEM_PROMPT}\n${m.content}${systemExtra}${jsonFmt}` } : m
        );
      } else {
        safeMessages = [{ role: "system", content: `${HANUI_SYSTEM_PROMPT}${systemExtra}${jsonFmt}` }, ...messages];
      }
    } else {
      safeMessages = [
        { role: "system", content: `${HANUI_SYSTEM_PROMPT}${systemExtra}${jsonFmt}` },
        {
          role: "user",
          content: `category:${category || "general"}\nquestion:${question || ""}\ncontext:\n${context || ""}`,
        },
      ];
    }

    let answer = "";
    let provider = "none";
    const mode = AI_ROUTER_MODE;

    if (mode === "n8n") {
      answer = await callN8n({
        question,
        category,
        context,
        messages: safeMessages,
        model,
        requestId: request_id,
        output_format,
      });
      provider = "n8n";
    } else if (mode === "openrouter") {
      answer = await callOpenRouter(safeMessages, model);
      provider = "openrouter";
    } else if (mode === "local") {
      answer = await callLocalModel(safeMessages, model);
      provider = "local";
    } else {
      // hybrid: n8n -> local -> openrouter (never call OpenRouter without a key)
      try {
        answer = await callN8n({
          question,
          category,
          context,
          messages: safeMessages,
          model,
          requestId: request_id,
          output_format,
        });
        provider = "n8n";
      } catch {
        try {
          answer = await callLocalModel(safeMessages, model);
          provider = "local";
        } catch {
          if (!OPENROUTER_API_KEY) {
            return res.status(503).json({
              success: false,
              error: "ai_backend_unconfigured",
              ai_router_mode: "hybrid",
              hint:
                "n8n/local failed or were not configured. Set OPENROUTER_API_KEY, or fix N8N_WEBHOOK_URL / LOCAL_LLM_URL.",
            });
          }
          answer = await callOpenRouter(safeMessages, model);
          provider = "openrouter";
        }
      }
    }

    if (AI_CHAT_GUARDS && answer) {
      const before = answer.length;
      answer = applyAnswerGuards(answer);
      if (answer.length < before) guardMeta.strips.push("cot_or_repeat");
    }

    const outputMeta = { format: output_format };
    if (output_format === "json") {
      if (!answer || !String(answer).trim()) {
        outputMeta.json_valid = false;
        outputMeta.json_error = "empty_answer";
      } else {
        const ex = extractFirstJSONObject(answer);
        if (ex.ok) {
          outputMeta.json_valid = true;
          outputMeta.parsed = ex.value;
          answer = JSON.stringify(ex.value, null, 2);
        } else {
          outputMeta.json_valid = false;
          outputMeta.json_error = ex.error;
          outputMeta.raw_excerpt = answer.slice(0, 600);
        }
      }
    }

    const payload = { success: true, provider, answer, guard: guardMeta, output: outputMeta };
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
