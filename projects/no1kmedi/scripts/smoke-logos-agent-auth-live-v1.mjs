/**
 * Live HTTP smoke: full service_auth chain on logos.jema-ai.com (or BASE).
 *   node scripts/smoke-logos-agent-auth-live-v1.mjs
 *   LOGOS_AGENT_AUTH_LIVE_BASE=https://logos.jema-ai.com node scripts/smoke-logos-agent-auth-live-v1.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../../..");
const BASE = (process.env.LOGOS_AGENT_AUTH_LIVE_BASE || "https://logos.jema-ai.com").replace(
  /\/$/,
  "",
);
const HDR = { "User-Agent": "MKM-LogosAgentAuthLiveSmoke/1.0", "Content-Type": "application/json" };
const OUT = path.join(ROOT, "reports", "logos_agent_auth_live_smoke_v1_latest.json");

const email = `live-smoke+${Date.now()}@no1kmedi.com`;

async function jsonFetch(url, init) {
  const res = await fetch(url, init);
  const body = await res.json().catch(() => ({}));
  return { res, body };
}

async function main() {
  const report = { schema: "logos_agent_auth_live_smoke_v1", base: BASE, ok: false, steps: [] };

  const reg = await jsonFetch(`${BASE}/api/agent/identity`, {
    method: "POST",
    headers: HDR,
    body: JSON.stringify({ type: "service_auth", login_hint: email }),
  });
  report.steps.push({ step: "register", status: reg.res.status, ok: reg.res.ok });
  if (!reg.res.ok) throw new Error(`register:${reg.res.status}:${JSON.stringify(reg.body)}`);

  const claimToken = reg.body.claim_token;
  const userCode = reg.body.claim?.user_code;
  const verificationUri = reg.body.claim?.verification_uri;
  const claimAttemptToken = new URL(String(verificationUri)).searchParams.get("claim_attempt_token");
  if (!claimToken || !userCode || !claimAttemptToken) throw new Error("missing_claim_fields");

  const pending = await jsonFetch(`${BASE}/api/agent/oauth2/token`, {
    method: "POST",
    headers: { ...HDR, "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:workos:agent-auth:grant-type:claim",
      claim_token: claimToken,
    }),
  });
  report.steps.push({
    step: "token_pending",
    status: pending.res.status,
    error: pending.body.error,
  });
  if (pending.body.error !== "authorization_pending") {
    throw new Error(`expected_pending:${JSON.stringify(pending.body)}`);
  }

  const complete = await jsonFetch(`${BASE}/api/agent/identity/claim/complete`, {
    method: "POST",
    headers: HDR,
    body: JSON.stringify({
      claim_attempt_token: claimAttemptToken,
      user_code: userCode,
      email,
    }),
  });
  report.steps.push({ step: "claim_complete", status: complete.res.status, ok: complete.res.ok });
  if (!complete.res.ok) throw new Error(`complete:${JSON.stringify(complete.body)}`);

  const token = await jsonFetch(`${BASE}/api/agent/oauth2/token`, {
    method: "POST",
    headers: { ...HDR, "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:workos:agent-auth:grant-type:claim",
      claim_token: claimToken,
    }),
  });
  report.steps.push({
    step: "token_ok",
    status: token.res.status,
    has_access_token: Boolean(token.body.access_token),
  });
  if (!token.res.ok || !token.body.access_token) throw new Error(`token:${JSON.stringify(token.body)}`);

  const query = await jsonFetch(`${BASE}/api/logos-research/presets`, {
    headers: {
      "User-Agent": HDR["User-Agent"],
      Authorization: `Bearer ${token.body.access_token}`,
    },
  });
  report.steps.push({
    step: "presets_bearer",
    status: query.res.status,
    pro: query.body.pro,
    ok: query.res.ok && query.body.ok === true,
  });
  if (!query.res.ok) throw new Error(`presets:${JSON.stringify(query.body)}`);

  report.ok = true;
  mkdirSync(path.dirname(OUT), { recursive: true });
  writeFileSync(OUT, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log("[smoke-logos-agent-auth-live] OK", OUT);
}

main().catch((err) => {
  console.error("[smoke-logos-agent-auth-live] FAIL", err);
  process.exit(1);
});
