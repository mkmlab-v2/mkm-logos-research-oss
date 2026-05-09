#!/usr/bin/env node

import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const marketingDir = path.resolve(__dirname, "..", "marketing-site");
const sourcePath = path.join(marketingDir, "public-copy.json");
const targetPath = path.join(marketingDir, "public-copy.bundle.js");

function stableStringify(value) {
  return JSON.stringify(value, null, 2);
}

try {
  const raw = await readFile(sourcePath, "utf8");
  const parsed = JSON.parse(raw);
  const payload = stableStringify(parsed);
  const bundle = [
    "/* AUTO-GENERATED FILE. DO NOT EDIT DIRECTLY. */",
    "/* Source: marketing-site/public-copy.json */",
    "window.__PUBLIC_COPY__ = " + payload + ";",
    "",
  ].join("\n");

  await writeFile(targetPath, bundle, "utf8");
  console.log("[sync-marketing-site-copy] wrote marketing-site/public-copy.bundle.js");
} catch (error) {
  console.error("[sync-marketing-site-copy] failed.");
  if (error instanceof Error && error.message) console.error(error.message);
  process.exitCode = 1;
}
