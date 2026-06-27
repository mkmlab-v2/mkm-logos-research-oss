/**
 * Offline + optional HTTP smoke: Logos agent-auth Tier C chain.
 *   npx --yes tsx ./scripts/smoke-logos-agent-auth-v1.ts
 *   LOGOS_AGENT_AUTH_SMOKE_BASE=http://127.0.0.1:3010 npx --yes tsx ./scripts/smoke-logos-agent-auth-v1.ts
 */
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  completeClaim,
  exchangeClaimToken,
  registerServiceAuth,
} from "../src/lib/logosAgentAuthV1";
import { verifyLogosAgentAccessToken } from "../src/lib/logosAgentAuthJwtV1";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const NO1K = path.resolve(__dirname, "..");
const ROOT = path.resolve(NO1K, "../..");
const OUT = path.join(ROOT, "reports", "logos_agent_auth_smoke_v1_latest.json");

process.env.LOGOS_AGENT_AUTH_DATA_DIR = path.join(
  ROOT,
  "reports",
  ".tmp_logos_agent_auth_smoke",
);
process.env.LOGOS_AGENT_AUTH_JWT_SECRET = "smoke-test-secret-v1";
rmSync(process.env.LOGOS_AGENT_AUTH_DATA_DIR, { recursive: true, force: true });
mkdirSync(process.env.LOGOS_AGENT_AUTH_DATA_DIR, { recursive: true });

const email = `agent-smoke+${Date.now()}@no1kmedi.com`;

async function offlineChain() {
  const reg = await registerServiceAuth({
    login_hint: email,
    origin: "http://127.0.0.1:3010",
  });
  if (!reg.ok) throw new Error(`register_failed:${JSON.stringify(reg.body)}`);

  const claimToken = String(reg.body.claim_token || "");
  const claim = reg.body.claim as { user_code?: string; verification_uri?: string };
  const userCode = String(claim.user_code || "");
  const claimAttemptToken = new URL(String(claim.verification_uri || "")).searchParams.get(
    "claim_attempt_token",
  );
  if (!claimToken || !userCode || !claimAttemptToken) {
    throw new Error("register_missing_claim_fields");
  }

  const pending = await exchangeClaimToken(claimToken);
  if (pending.ok || pending.body.error !== "authorization_pending") {
    throw new Error(`expected_authorization_pending:${JSON.stringify(pending.body)}`);
  }

  const done = await completeClaim({
    claim_attempt_token: claimAttemptToken,
    user_code: userCode,
    email,
  });
  if (!done.ok) throw new Error(`complete_failed:${JSON.stringify(done.body)}`);

  const token = await exchangeClaimToken(claimToken);
  if (!token.ok) throw new Error(`token_failed:${JSON.stringify(token.body)}`);

  const access = String(token.body.access_token || "");
  const claims = verifyLogosAgentAccessToken(access);
  if (!claims?.scopes.includes("logos.query.read")) {
    throw new Error("token_missing_query_scope");
  }

  return {
    registration_id: reg.body.registration_id,
    scopes: claims.scopes,
    expires_in: token.body.expires_in,
  };
}

async function httpDiscovery(base: string) {
  const hdr = { "User-Agent": "MKM-LogosAgentAuthSmoke/1.0" };
  const prm = await fetch(`${base}/.well-known/oauth-protected-resource`, { headers: hdr });
  const as = await fetch(`${base}/.well-known/oauth-authorization-server`, { headers: hdr });
  const prmJson = await prm.json();
  const asJson = await as.json();
  if (!prm.ok || !as.ok) throw new Error(`discovery_http_fail prm=${prm.status} as=${as.status}`);
  if (asJson.implementation_status !== "tier_c_service_auth") {
    throw new Error(`unexpected_impl_status:${asJson.implementation_status}`);
  }
  return { prm_status: prm.status, as_status: as.status, endpoints_status: asJson.agent_auth?.endpoints_status };
}

async function main() {
  const base = (process.env.LOGOS_AGENT_AUTH_SMOKE_BASE || "").replace(/\/$/, "");
  const report: Record<string, unknown> = {
    schema: "logos_agent_auth_smoke_v1",
    ok: false,
    offline: null as unknown,
    http: null as unknown,
  };

  report.offline = await offlineChain();

  process.env.LOGOS_AGENT_AUTH_EMAIL_DOMAIN_ALLOWLIST = "no1kmedi.com";
  const blocked = await registerServiceAuth({ login_hint: "blocked@evil.example", origin: "http://127.0.0.1" });
  if (blocked.ok || blocked.status !== 403) {
    throw new Error(`domain_allowlist_expected_403:${JSON.stringify(blocked)}`);
  }
  delete process.env.LOGOS_AGENT_AUTH_EMAIL_DOMAIN_ALLOWLIST;

  if (base) {
    report.http = await httpDiscovery(base);
  }
  report.ok = true;
  writeFileSync(OUT, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log("[smoke-logos-agent-auth] OK", OUT);
}

main().catch((err) => {
  console.error("[smoke-logos-agent-auth] FAIL", err);
  process.exit(1);
});
