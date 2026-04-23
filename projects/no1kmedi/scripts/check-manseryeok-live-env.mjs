#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const raw = fs.readFileSync(filePath, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx <= 0) continue;
    const key = trimmed.slice(0, idx).trim();
    const value = trimmed.slice(idx + 1).trim();
    if (!key || process.env[key] !== undefined) continue;
    process.env[key] = value;
  }
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
loadEnvFile(path.resolve(scriptDir, "../.env.local"));
loadEnvFile(path.resolve(scriptDir, "../../../.env"));

const url = process.env.ATHENA_MANSERYEOK_API_URL;
const token = process.env.ATHENA_MANSERYEOK_API_TOKEN?.trim();

function fail(message) {
  console.error(`check-manseryeok-live-env failed: ${message}`);
  process.exit(1);
}

async function main() {
  if (!url) fail("ATHENA_MANSERYEOK_API_URL is required");

  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    fail("ATHENA_MANSERYEOK_API_URL must be a valid URL");
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    fail("ATHENA_MANSERYEOK_API_URL must use http/https");
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "x-api-token": token } : {}),
      },
      body: JSON.stringify({
        birth_instant_utc: "1987-12-31T15:00:00Z",
        iana_tz: "Asia/Seoul",
        birth_datetime: "1988-01-03 06:30",
      }),
      signal: controller.signal,
    });
    if (!res.ok) fail(`endpoint probe failed with status ${res.status}`);

    const json = await res.json();
    if (!json || typeof json.saju_label !== "string" || json.saju_label.trim().length === 0) {
      fail("endpoint must return a non-empty saju_label");
    }
  } catch (error) {
    fail(error.message);
  } finally {
    clearTimeout(timeout);
  }

  console.log("check-manseryeok-live-env passed");
}

main();
