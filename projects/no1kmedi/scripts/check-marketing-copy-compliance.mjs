#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const copyPath = path.resolve(__dirname, "..", "marketing-site", "public-copy.json");

const prohibitedPatterns = [
  /guaranteed cure/i,
  /100% cure/i,
  /best in korea/i,
  /permanent cure/i,
];

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

try {
  const raw = await readFile(copyPath, "utf8");
  const parsed = JSON.parse(raw);
  const textLines = collectStrings(parsed);
  const violations = textLines.filter((line) =>
    prohibitedPatterns.some((pattern) => pattern.test(line)),
  );

  if (violations.length > 0) {
    console.error("[check-marketing-copy] compliance violation detected.");
    for (const line of violations) console.error(`- ${line}`);
    process.exitCode = 1;
  } else {
    console.log("[check-marketing-copy] passed.");
  }
} catch (error) {
  console.error("[check-marketing-copy] failed to validate marketing copy.");
  if (error instanceof Error && error.message) console.error(error.message);
  process.exitCode = 1;
}
