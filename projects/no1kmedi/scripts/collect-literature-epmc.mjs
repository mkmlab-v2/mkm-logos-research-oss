#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";

function arg(name, fallback = "") {
  const idx = process.argv.indexOf(name);
  if (idx < 0) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

const query = arg("--query", "(traditional medicine) AND (clinical)");
const pageSize = Number(arg("--page-size", "25"));
const maxPages = Number(arg("--max-pages", "2"));
const out = arg(
  "--out",
  path.join(process.cwd(), "memory", "literature", "epmc_raw_latest.json"),
);

async function fetchPage(page) {
  const url = new URL("https://www.ebi.ac.uk/europepmc/webservices/rest/search");
  url.searchParams.set("query", query);
  url.searchParams.set("format", "json");
  url.searchParams.set("pageSize", String(pageSize));
  url.searchParams.set("page", String(page));
  const res = await fetch(url);
  if (!res.ok) throw new Error(`epmc_http_${res.status}`);
  return res.json();
}

async function main() {
  const pages = [];
  for (let p = 1; p <= Math.max(1, maxPages); p += 1) {
    const json = await fetchPage(p);
    const results = json?.resultList?.result ?? [];
    pages.push({ page: p, count: results.length, raw: json });
    if (!results.length) break;
  }

  const rows = pages.flatMap((x) => x.raw?.resultList?.result ?? []);
  const payload = {
    schema: "epmc_raw_collection_v1",
    generated_at_utc: new Date().toISOString(),
    query,
    page_size: pageSize,
    max_pages: maxPages,
    row_count: rows.length,
    pages: pages.map((p) => ({ page: p.page, count: p.count })),
    rows,
  };

  await fs.mkdir(path.dirname(out), { recursive: true });
  await fs.writeFile(out, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  process.stdout.write(`wrote ${out} (rows=${rows.length})\n`);
}

main().catch((err) => {
  process.stderr.write(`${err instanceof Error ? err.message : String(err)}\n`);
  process.exit(2);
});

