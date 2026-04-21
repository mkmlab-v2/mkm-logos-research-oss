#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const copyPath = path.resolve(__dirname, "..", "marketing-site", "public-copy.json");

const disallowedClaims = [
  /diagnose you automatically/i,
  /replace doctor/i,
  /medical diagnosis guaranteed/i,
  /instant prescription/i,
];

function flattenText(value, out = []) {
  if (typeof value === "string") {
    out.push(value);
    return out;
  }
  if (Array.isArray(value)) {
    for (const item of value) flattenText(item, out);
    return out;
  }
  if (value && typeof value === "object") {
    for (const child of Object.values(value)) flattenText(child, out);
  }
  return out;
}

try {
  const raw = await readFile(copyPath, "utf8");
  const parsed = JSON.parse(raw);
  const lines = flattenText(parsed);
  const matches = lines.filter((line) =>
    disallowedClaims.some((pattern) => pattern.test(line)),
  );

  if (matches.length > 0) {
    console.error("[check-trackc-claims] disallowed claim text found.");
    for (const line of matches) console.error(`- ${line}`);
    process.exitCode = 1;
  } else {
    console.log("[check-trackc-claims] passed.");
  }
} catch (error) {
  console.error("[check-trackc-claims] validation failed.");
  if (error instanceof Error && error.message) console.error(error.message);
  process.exitCode = 1;
}
