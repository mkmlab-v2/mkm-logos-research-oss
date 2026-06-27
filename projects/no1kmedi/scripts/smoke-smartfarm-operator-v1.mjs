#!/usr/bin/env node
/**
 * Smoke: /smartfarm/operator page + API proxy health (optional upstream).
 * Usage: node scripts/smoke-smartfarm-operator-v1.mjs [--base http://127.0.0.1:3020]
 */
const base = (process.argv.find((a) => a.startsWith("--base="))?.split("=")[1] ||
  process.env.SMOKE_BASE ||
  "http://127.0.0.1:3020"
).replace(/\/$/, "");

async function main() {
  const page = await fetch(`${base}/smartfarm/operator`, { redirect: "follow" });
  if (!page.ok) {
    console.error("FAIL operator page", page.status);
    process.exit(1);
  }
  const html = await page.text();
  if (!html.includes("sf-operator-page") && !html.includes("농장 운영")) {
    console.error("FAIL operator markup missing");
    process.exit(1);
  }

  const health = await fetch(`${base}/api/smartfarm/health`);
  const healthBody = await health.json().catch(() => ({}));
  if (health.ok) {
    console.log("OK api proxy + upstream", healthBody.status ?? "ok");
  } else {
    console.log("WARN api proxy upstream down (expected without stub):", health.status, healthBody.error);
  }

  console.log("OK smartfarm operator smoke", base);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
