/**
 * Production API diagnostics (health + router aliases).
 * CI: .github/workflows/no1kmedi-api-smoke.yml
 * Env: API_BASE (required), e.g. https://api.no1kmedi.com
 */
const base = (process.env.API_BASE || "").trim().replace(/\/$/, "");
if (!base) {
  console.error(JSON.stringify({ ok: false, error: "API_BASE is required" }));
  process.exit(1);
}

/** SSOT: docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md §VPS */
const paths = ["/health", "/api/ai/router-status", "/router-status"];

async function probe(path) {
  const url = `${base}${path}`;
  try {
    const res = await fetch(url, { method: "GET" });
    const text = (await res.text()).slice(0, 400);
    let json = null;
    try {
      json = JSON.parse(text);
    } catch {
      json = { raw: text };
    }
    return { path, url, status: res.status, ok: res.ok, body: json };
  } catch (err) {
    return { path, url, ok: false, error: String(err) };
  }
}

const results = [];
for (const p of paths) {
  results.push(await probe(p));
}

const blocked = results.some(
  (r) =>
    r.body?.raw?.includes("hcdn-cgi") ||
    r.body?.raw?.includes("Checking your browser") ||
    (r.status === 404 && r.body?.raw?.includes("<!DOCTYPE html"))
);
const ok = results.some((r) => r.ok);
const out = {
  ok,
  schema: "no1kmedi_diagnose_prod_v1",
  api_base: base,
  generated_at: new Date().toISOString(),
  infrastructure_note: blocked
    ? "No payapp JSON health; likely Cloudflare challenge or Hostinger default vhost — verify on VPS: curl -sS https://api.no1kmedi.com/health (SSOT NO1KMEDI §VPS)."
    : null,
  probes: results,
};
console.log(JSON.stringify(out, null, 2));
process.exit(ok ? 0 : 1);
