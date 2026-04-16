import http from "node:http";

const port = Number(process.env.PORT || 3000);
const apiToken = (process.env.MANSERYEOK_API_TOKEN || "").trim();
const rateLimitMax = Number(process.env.MANSERYEOK_RATE_LIMIT_MAX || 120);
const rateLimitWindowMs = Number(process.env.MANSERYEOK_RATE_LIMIT_WINDOW_MS || 60_000);
const rateLimitWindow = new Map();

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

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  if (req.method !== "POST" || req.url !== "/manseryeok/reference") {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ success: false, error: "not_found" }));
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
      res.writeHead(401, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ success: false, error: "unauthorized" }));
      return;
    }
  }

  let body = "";
  req.on("data", (chunk) => {
    body += chunk.toString();
  });

  req.on("end", () => {
    let payload = {};
    try {
      payload = JSON.parse(body || "{}");
    } catch {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ success: false, error: "invalid_json" }));
      return;
    }

    const birthDatetime = payload.birth_datetime;
    if (typeof birthDatetime !== "string" || birthDatetime.trim().length === 0) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ success: false, error: "birth_datetime is required" }));
      return;
    }

    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        success: true,
        saju_label: makeSajuLabel(birthDatetime),
      }),
    );
  });
});

server.listen(port, () => {
  console.log(`hostinger-manseryeok-api running on port ${port}`);
});
