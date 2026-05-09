#!/usr/bin/env node
/**
 * GET /api/guardian/beta-ops/status — needs running Next (npm run dev) and matching admin token on server + client env.
 *
 * Env (client, must match server):
 *   MKMLIFE_BETA_ADMIN_TOKEN or NO1KMEDI_ADMIN_TOKEN
 * Optional:
 *   NO1KMEDI_BASE_URL (default http://127.0.0.1:3010)
 */
const BASE_URL = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");

function clientToken() {
  return String(process.env.MKMLIFE_BETA_ADMIN_TOKEN || process.env.NO1KMEDI_ADMIN_TOKEN || "").trim();
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  const t = clientToken();
  if (!t) {
    console.error(
      "Set MKMLIFE_BETA_ADMIN_TOKEN or NO1KMEDI_ADMIN_TOKEN (must match the token configured on the Next server).",
    );
    process.exit(1);
  }

  const res = await fetch(`${BASE_URL}/api/guardian/beta-ops/status`, {
    method: "GET",
    headers: { Authorization: `Bearer ${t}` },
  });
  const json = await res.json().catch(() => ({}));

  if (res.status === 503 && json?.error === "admin_token_not_configured") {
    console.error(
      "Server has no admin token: set MKMLIFE_BETA_ADMIN_TOKEN or NO1KMEDI_ADMIN_TOKEN for the Next process, then retry.",
    );
    process.exit(1);
  }
  if (res.status === 401) {
    console.error("401 unauthorized — client token does not match server (or server rejected Bearer).");
    process.exit(1);
  }

  assert(res.status === 200, `expected 200, got ${res.status}: ${JSON.stringify(json)}`);
  assert(json?.success === true, "response.success must be true");
  assert(typeof json?.date_utc === "string", "date_utc required");
  assert(typeof json?.beta_mode_enabled === "boolean", "beta_mode_enabled required");
  assert(typeof json?.cap_per_identity_daily === "number", "cap_per_identity_daily required");
  assert(json?.usage && typeof json.usage === "object", "usage object required");

  console.log(
    `smoke-mkmlife-beta-ops passed (${BASE_URL}) date_utc=${json.date_utc} beta_mode=${json.beta_mode_enabled} cap=${json.cap_per_identity_daily}`,
  );
}

main().catch((error) => {
  console.error("smoke-mkmlife-beta-ops failed:", error.message);
  process.exit(1);
});
