#!/usr/bin/env node
/**
 * Smoke: POST /api/manseryeok/reference (workspace Python engine).
 * Requires MKM_WORKSPACE_ROOT or discovery of scripts/run_saju_global_birth_v1.py from cwd ancestry.
 */
const baseUrl = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");
const token = process.env.MANSERYEOK_REFERENCE_TOKEN?.trim();

async function main() {
  const res = await fetch(`${baseUrl}/api/manseryeok/reference`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...(token ? { "x-api-token": token } : {}),
    },
    body: JSON.stringify({
      birth_instant_utc: "1991-03-10T02:10:00Z",
      iana_tz: "Asia/Seoul",
    }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    console.error("[smoke:manseryeok-reference] failed", res.status, json);
    process.exit(1);
  }
  if (typeof json.saju_label !== "string" || !json.saju_label.trim()) {
    console.error("[smoke:manseryeok-reference] missing saju_label", json);
    process.exit(1);
  }
  console.log("[smoke:manseryeok-reference] ok", json.saju_label.slice(0, 80));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
