/**
 * Preflight: Next dev must serve main-app.js (client hydration) before Playwright ask smoke.
 * Usage: node ./scripts/check-logos-inquiry-dev-chunks-v1.mjs [--base http://localhost:3035]
 */
const base = (
  process.argv.find((a) => a.startsWith("--base="))?.slice(7) ||
  process.argv[process.argv.indexOf("--base") + 1] ||
  "http://localhost:3010"
).replace(/\/$/, "");

async function main() {
  const pageRes = await fetch(`${base}/logos-research/ask`);
  if (!pageRes.ok) {
    console.log(JSON.stringify({ ok: false, step: "ask_page", status: pageRes.status, base }));
    process.exit(1);
  }
  const html = await pageRes.text();
  const match = html.match(/\/_next\/static\/chunks\/main-app\.js[^"']*/);
  if (!match) {
    console.log(JSON.stringify({ ok: false, step: "main_app_href_missing", base }));
    process.exit(1);
  }
  const chunkUrl = match[0].startsWith("http") ? match[0] : `${base}${match[0]}`;
  const chunkRes = await fetch(chunkUrl);
  const ok = chunkRes.ok;
  console.log(
    JSON.stringify({
      ok,
      base,
      chunk_url: chunkUrl,
      chunk_status: chunkRes.status,
      hint: ok ? null : "rm -rf .next && npm run dev:logos (stale dev chunk 404)",
    }),
  );
  process.exit(ok ? 0 : 1);
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: String(err) }));
  process.exit(1);
});
