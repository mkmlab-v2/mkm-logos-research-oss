#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const copyPath = path.resolve(__dirname, "..", "marketing-site", "public-copy.json");
const linkedinDraftsDir = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "reports",
  "marketing",
  "linkedin_drafts",
);

const prohibitedPatterns = [
  /guaranteed cure/i,
  /100% cure/i,
  /best in korea/i,
  /permanent cure/i,
  /guaranteed returns?/i,
  /hallucination eliminated/i,
  /neuroscience[- ]proven/i,
  /always profitable/i,
  /수익 보장/,
  /환각 제거/,
];

/** Lines that mention banned phrases only to disclaim them (PUBLIC_FACING v1.7). */
function lineIsDisclaimerContext(line) {
  if (/\b(no|not)\b/i.test(line) && /guarantee|보장/i.test(line)) return true;
  if (/금지|없음|아님|쓰지\s*않|제공하지\s*않|하지\s*않습니다|표현을\s*쓰지|주장하지\s*않/i.test(line) && /guarantee|보장|환각/i.test(line)) {
    return true;
  }
  return false;
}

function lineViolatesCompliance(line) {
  if (lineIsDisclaimerContext(line)) return false;
  return prohibitedPatterns.some((pattern) => pattern.test(line));
}

/** PUBLIC_FACING v1.7 — consumer-visible legacy brand noise (URLs with no1kmedi.com are OK). */
function surfaceBrandViolation(line) {
  const s = line.trim();
  if (!s) return false;
  if (/^https?:\/\//i.test(s)) return false;
  if (/\(no1kmedi\)/i.test(s)) return true;
  if (/no1kmedi\s+ai/i.test(s)) return true;
  if (/(?<![./\w])no1kmedi(?!\.com)/i.test(s)) return true;
  return false;
}

function collectStrings(value, bucket = []) {
  if (typeof value === "string") {
    bucket.push(value);
    return bucket;
  }
  if (Array.isArray(value)) {
    for (const item of value) collectStrings(item, bucket);
    return bucket;
  }
  if (value && typeof value === "object") {
    for (const nested of Object.values(value)) collectStrings(nested, bucket);
  }
  return bucket;
}

async function scanLinkedinDrafts() {
  const { readdir } = await import("node:fs/promises");
  let names = [];
  try {
    names = await readdir(linkedinDraftsDir);
  } catch {
    return [];
  }
  const hits = [];
  for (const name of names) {
    if (!name.endsWith("_[DRAFT].md")) continue;
    const full = path.join(linkedinDraftsDir, name);
    const text = await readFile(full, "utf8");
    if (!/\[DRAFT\]/i.test(text)) {
      hits.push(`${name}: missing [DRAFT] marker`);
    }
    for (const line of text.split(/\r?\n/)) {
      if (lineViolatesCompliance(line)) {
        hits.push(`${name}: ${line.slice(0, 120)}`);
      }
    }
  }
  return hits;
}

try {
  const raw = await readFile(copyPath, "utf8");
  const parsed = JSON.parse(raw);
  const textLines = collectStrings(parsed);
  const violations = textLines.filter((line) => lineViolatesCompliance(line));
  const surfaceHits = textLines.filter((line) => surfaceBrandViolation(line));
  const draftHits = await scanLinkedinDrafts();

  if (violations.length > 0 || surfaceHits.length > 0 || draftHits.length > 0) {
    console.error("[check-marketing-copy] compliance violation detected.");
    for (const line of violations) console.error(`- public-copy: ${line}`);
    for (const line of surfaceHits) console.error(`- public-copy surface-brand: ${line}`);
    for (const line of draftHits) console.error(`- linkedin-draft: ${line}`);
    process.exitCode = 1;
  } else {
    console.log("[check-marketing-copy] passed.");
  }
} catch (error) {
  console.error("[check-marketing-copy] failed to validate marketing copy.");
  if (error instanceof Error && error.message) console.error(error.message);
  process.exitCode = 1;
}
