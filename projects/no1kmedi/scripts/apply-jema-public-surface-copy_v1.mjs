#!/usr/bin/env node
/**
 * Idempotent PUBLIC_FACING surface detox for marketing-site/public-copy.json.
 * Replaces consumer-visible legacy brand noise; does not change href hostnames.
 */
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const copyPath = path.resolve(__dirname, "..", "marketing-site", "public-copy.json");

const REPLACEMENTS = [
  { from: /한의사 포털 \(no1kmedi\)/g, to: "한의사 진료 보조 (JEMA AI)" },
  { from: /\(no1kmedi\)/gi, to: "(JEMA AI)" },
  { from: /no1kmedi\s+AI/gi, to: "JEMA AI" },
];

function applyToStrings(value, stats) {
  if (typeof value === "string") {
    let next = value;
    if (/^https?:\/\//i.test(value.trim())) {
      return value;
    }
    for (const { from, to } of REPLACEMENTS) {
      if (from.test(next)) {
        next = next.replace(from, to);
        stats.replacements += 1;
      }
    }
    return next;
  }
  if (Array.isArray(value)) {
    return value.map((item) => applyToStrings(item, stats));
  }
  if (value && typeof value === "object") {
    const out = {};
    for (const [key, nested] of Object.entries(value)) {
      out[key] = applyToStrings(nested, stats);
    }
    return out;
  }
  return value;
}

try {
  const raw = await readFile(copyPath, "utf8");
  const parsed = JSON.parse(raw);
  const stats = { replacements: 0 };
  const next = applyToStrings(parsed, stats);
  const out = `${JSON.stringify(next, null, 2)}\n`;
  if (out !== raw) {
    await writeFile(copyPath, out, "utf8");
    console.log(`[apply-jema-public-surface-copy] updated ${copyPath} (${stats.replacements} pattern hits)`);
  } else {
    console.log("[apply-jema-public-surface-copy] no changes needed.");
  }
} catch (error) {
  console.error("[apply-jema-public-surface-copy] failed.");
  if (error instanceof Error && error.message) console.error(error.message);
  process.exitCode = 1;
}
