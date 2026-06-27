#!/usr/bin/env node
/**
 * Smoke: POST /api/myeongni/studio-full-report-v1 (summary only).
 */
const baseUrl = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3020").replace(/\/$/, "");

async function main() {
  const res = await fetch(`${baseUrl}/api/myeongni/studio-full-report-v1`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      year: 1991,
      month: 3,
      day: 10,
      hour: 11,
      minute: 10,
      tz: "Asia/Seoul",
      is_male: true,
      is_solar: true,
    }),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok || !json.success) {
    console.error("[smoke:myeongni-studio-full-report] failed", res.status, json);
    process.exit(1);
  }
  if (json.send_gate !== "HOLD" || !json.summary) {
    console.error("[smoke:myeongni-studio-full-report] invalid payload", json);
    process.exit(1);
  }
  console.log("[smoke:myeongni-studio-full-report] ok", json.summary.schema);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
