#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { gzipSync } from "node:zlib";

function arg(name, fallback = "") {
  const idx = process.argv.indexOf(name);
  if (idx < 0) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

const inputPath = arg(
  "--in",
  path.join(process.cwd(), "memory", "literature", "epmc_raw_latest.json"),
);
const outJsonl = arg(
  "--out-jsonl",
  path.join(process.cwd(), "memory", "literature", "literature_memory_snapshot_latest.jsonl"),
);
const outSummary = arg(
  "--out-summary",
  path.join(process.cwd(), "memory", "literature", "literature_memory_snapshot_summary_latest.json"),
);
const outIndex = arg(
  "--out-index",
  path.join(process.cwd(), "memory", "literature", "literature_memory_search_index_latest.json"),
);
const outArchiveGzip = arg(
  "--out-archive-gzip",
  path.join(process.cwd(), "memory", "literature", "literature_memory_snapshot_latest.jsonl.gz"),
);

function sha256(s) {
  return createHash("sha256").update(s || "").digest("hex");
}

function normalizeRow(row) {
  const title = String(row?.title || "").trim();
  const abstract = String(row?.abstractText || "").trim();
  const source = String(row?.source || "").trim();
  const id = String(row?.id || "").trim();
  const doi = String(row?.doi || "").trim();
  const year = String(row?.pubYear || "").trim();
  const evidenceId = `${source}:${id || doi || sha256(title).slice(0, 12)}`;
  const snippet = abstract || title;
  return {
    schema: "literature_memory_item_v1",
    evidence_id: evidenceId,
    title,
    year,
    source,
    source_id: id || doi || "",
    doi,
    uri: row?.fullTextUrlList?.fullTextUrl?.[0]?.url || "",
    snippet,
    snippet_hash: sha256(snippet),
    title_hash: sha256(title),
    ingested_at_utc: new Date().toISOString(),
  };
}

function tokenizeForIndex(text) {
  const tokens = String(text || "")
    .toLowerCase()
    .split(/[^a-z0-9가-힣]+/g)
    .map((x) => x.trim())
    .filter((x) => x.length >= 2);
  return Array.from(new Set(tokens)).slice(0, 64);
}

async function main() {
  const raw = JSON.parse(await fs.readFile(inputPath, "utf8"));
  const rows = Array.isArray(raw?.rows) ? raw.rows : [];
  const norm = rows.map(normalizeRow).filter((x) => x.title || x.snippet);

  // Deduplicate by evidence_id preferring first seen
  const seen = new Set();
  const unique = [];
  for (const item of norm) {
    if (seen.has(item.evidence_id)) continue;
    seen.add(item.evidence_id);
    unique.push(item);
  }

  await fs.mkdir(path.dirname(outJsonl), { recursive: true });
  const jsonl = unique.map((x) => JSON.stringify(x)).join("\n");
  await fs.writeFile(outJsonl, `${jsonl}\n`, "utf8");
  await fs.writeFile(outArchiveGzip, gzipSync(`${jsonl}\n`));

  const docFreqMap = new Map();
  const titleDocFreqMap = new Map();
  const snippetDocFreqMap = new Map();
  let totalDocTerms = 0;
  let totalTitleTerms = 0;
  let totalSnippetTerms = 0;
  const indexedItems = unique.map((item) => {
    const titleTerms = tokenizeForIndex(item.title || "");
    const snippetTerms = tokenizeForIndex(item.snippet || "");
    const searchTerms = Array.from(new Set([...titleTerms, ...snippetTerms])).slice(0, 64);
    totalDocTerms += searchTerms.length;
    totalTitleTerms += titleTerms.length;
    totalSnippetTerms += snippetTerms.length;
    for (const term of searchTerms) {
      docFreqMap.set(term, (docFreqMap.get(term) || 0) + 1);
    }
    for (const term of titleTerms) {
      titleDocFreqMap.set(term, (titleDocFreqMap.get(term) || 0) + 1);
    }
    for (const term of snippetTerms) {
      snippetDocFreqMap.set(term, (snippetDocFreqMap.get(term) || 0) + 1);
    }
    return {
      evidence_id: item.evidence_id,
      title: item.title,
      snippet: item.snippet,
      source: item.source,
      source_id: item.source_id,
      snippet_hash: item.snippet_hash,
      uri: item.uri,
      title_terms: titleTerms,
      snippet_terms: snippetTerms,
      search_terms: searchTerms,
    };
  });

  const avgDocTerms = indexedItems.length > 0 ? totalDocTerms / indexedItems.length : 0;
  const avgTitleTerms = indexedItems.length > 0 ? totalTitleTerms / indexedItems.length : 0;
  const avgSnippetTerms = indexedItems.length > 0 ? totalSnippetTerms / indexedItems.length : 0;

  const indexPayload = {
    schema: "literature_memory_search_index_v1",
    generated_at_utc: new Date().toISOString(),
    source_snapshot_path: outJsonl,
    item_count: unique.length,
    corpus_meta: {
      document_count: indexedItems.length,
      avg_doc_terms: avgDocTerms,
      avg_title_terms: avgTitleTerms,
      avg_snippet_terms: avgSnippetTerms,
      token_doc_freq: Object.fromEntries(docFreqMap),
      title_token_doc_freq: Object.fromEntries(titleDocFreqMap),
      snippet_token_doc_freq: Object.fromEntries(snippetDocFreqMap),
    },
    items: indexedItems,
  };
  await fs.writeFile(outIndex, `${JSON.stringify(indexPayload)}\n`, "utf8");

  const summary = {
    schema: "literature_memory_snapshot_summary_v1",
    generated_at_utc: new Date().toISOString(),
    source_file: inputPath,
    out_jsonl: outJsonl,
    out_index: outIndex,
    out_archive_gzip: outArchiveGzip,
    row_count_raw: rows.length,
    row_count_normalized: norm.length,
    row_count_unique: unique.length,
    sample_evidence_ids: unique.slice(0, 5).map((x) => x.evidence_id),
  };
  await fs.writeFile(outSummary, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
  process.stdout.write(`wrote ${outJsonl} (unique=${unique.length})\n`);
  process.stdout.write(`wrote ${outSummary}\n`);
}

main().catch((err) => {
  process.stderr.write(`${err instanceof Error ? err.message : String(err)}\n`);
  process.exit(2);
});

