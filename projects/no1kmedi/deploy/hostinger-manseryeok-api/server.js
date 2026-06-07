import http from "node:http";
import { runVerifyLiteEngine } from "./verify-lite-engine.mjs";

const port = Number(process.env.PORT || 3000);
const apiToken = (process.env.MANSERYEOK_API_TOKEN || "").trim();
const rateLimitMax = Number(process.env.MANSERYEOK_RATE_LIMIT_MAX || 120);
const rateLimitWindowMs = Number(process.env.MANSERYEOK_RATE_LIMIT_WINDOW_MS || 60_000);
const rateLimitWindow = new Map();
const workspaceRoot = (process.env.MKM_WORKSPACE_ROOT || "").trim();

function makeSajuLabel(value = "") {
  const text = String(value);
  const score = Array.from(text).reduce((sum, ch) => sum + ch.charCodeAt(0), 0);
  const stems = ["목", "화", "토", "금", "수"];
  return `${stems[score % stems.length]}기 편중 경향`;
}

function readClientIp(req) {
  const forwarded = req.headers["x-forwarded-for"];
  if (typeof forwarded === "string" && forwarded.trim()) {
    return forwarded.split(",")[0].trim();
  }
  const realIp = req.headers["x-real-ip"];
  if (typeof realIp === "string" && realIp.trim()) {
    return realIp.trim();
  }
  return req.socket?.remoteAddress || "unknown";
}

function checkRateLimit(ip) {
  const now = Date.now();
  const entry = rateLimitWindow.get(ip);
  if (!entry || now > entry.resetAt) {
    rateLimitWindow.set(ip, { count: 1, resetAt: now + rateLimitWindowMs });
    return { allowed: true, retryAfterSeconds: 0 };
  }
  if (entry.count >= rateLimitMax) {
    return { allowed: false, retryAfterSeconds: Math.max(1, Math.ceil((entry.resetAt - now) / 1000)) };
  }
  entry.count += 1;
  rateLimitWindow.set(ip, entry);
  return { allowed: true, retryAfterSeconds: 0 };
}

function readToken(req) {
  const tokenHeader = req.headers["x-api-token"];
  if (typeof tokenHeader === "string" && tokenHeader.trim()) return tokenHeader.trim();
  const auth = req.headers.authorization;
  if (typeof auth === "string" && auth.toLowerCase().startsWith("bearer ")) {
    return auth.slice(7).trim();
  }
  return "";
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk.toString();
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(body || "{}"));
      } catch {
        reject(new Error("invalid_json"));
      }
    });
    req.on("error", reject);
  });
}

function jsonResponse(res, status, payload) {
  res.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" });
  res.end(JSON.stringify(payload));
}

async function handleVerifyLite(req, res, payload) {
  if (!workspaceRoot) {
    jsonResponse(res, 503, {
      success: false,
      error: "workspace_root_not_found",
      hint: "Set MKM_WORKSPACE_ROOT on VPS to monorepo root with scripts/saju_askone_verify_bundle_v1.py",
    });
    return;
  }

  const tz = payload.tz || payload.iana_tz;
  if (typeof tz !== "string" || !tz.trim()) {
    jsonResponse(res, 400, { success: false, error: "tz_required" });
    return;
  }

  try {
    const doc = await runVerifyLiteEngine({
      birth_instant_utc: payload.birth_instant_utc,
      year: payload.year,
      month: payload.month,
      day: payload.day,
      hour: payload.hour,
      minute: payload.minute,
      tz: tz.trim(),
      is_solar: payload.is_solar,
      is_male: payload.is_male,
      secondary_day_rollover_policy: payload.secondary_day_rollover_policy,
    });
    jsonResponse(res, 200, { success: true, ...doc, source: "hostinger-manseryeok-api" });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const isRoot = msg.includes("workspace_root_not_found");
    jsonResponse(res, isRoot ? 503 : 500, {
      success: false,
      error: isRoot ? "workspace_root_not_found" : "engine_runtime_error",
      message: msg.slice(0, 400),
    });
  }
}

const server = http.createServer(async (req, res) => {
  if (req.method === "GET" && req.url === "/health") {
    jsonResponse(res, 200, { ok: true, verify_lite_engine: Boolean(workspaceRoot) });
    return;
  }

  const isReference = req.method === "POST" && req.url === "/manseryeok/reference";
  const isVerifyLite = req.method === "POST" && req.url === "/manseryeok/verify-lite";

  if (!isReference && !isVerifyLite) {
    jsonResponse(res, 404, { success: false, error: "not_found" });
    return;
  }

  const limiter = checkRateLimit(readClientIp(req));
  if (!limiter.allowed) {
    res.writeHead(429, {
      "Content-Type": "application/json",
      "Retry-After": String(limiter.retryAfterSeconds),
    });
    res.end(JSON.stringify({ success: false, error: "rate_limited", retry_after_seconds: limiter.retryAfterSeconds }));
    return;
  }

  if (apiToken) {
    const providedToken = readToken(req);
    if (!providedToken || providedToken !== apiToken) {
      jsonResponse(res, 401, { success: false, error: "unauthorized" });
      return;
    }
  }

  let payload;
  try {
    payload = await readJsonBody(req);
  } catch {
    jsonResponse(res, 400, { success: false, error: "invalid_json" });
    return;
  }

  if (isVerifyLite) {
    await handleVerifyLite(req, res, payload);
    return;
  }

  const birthDatetime = payload.birth_datetime;
  const utc = payload.birth_instant_utc;
  const ianaTz = payload.iana_tz;
  const useGlobal =
    typeof utc === "string" &&
    utc.trim().length > 0 &&
    typeof ianaTz === "string" &&
    ianaTz.trim().length > 0;
  const seed = useGlobal ? `${utc.trim()}|${ianaTz.trim()}` : birthDatetime;
  if (typeof seed !== "string" || seed.trim().length === 0) {
    jsonResponse(res, 400, {
      success: false,
      error: "provide birth_instant_utc+iana_tz or birth_datetime",
    });
    return;
  }

  jsonResponse(res, 200, {
    success: true,
    saju_label: makeSajuLabel(seed),
    source: workspaceRoot ? "legacy-stub-label" : "legacy-stub-label",
  });
});

server.listen(port, () => {
  console.log(`hostinger-manseryeok-api running on port ${port} (verify-lite engine=${Boolean(workspaceRoot)})`);
});
