#!/usr/bin/env node
import { spawn } from "node:child_process";
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

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: "inherit",
      shell: process.platform === "win32",
      env: process.env,
    });
    child.on("exit", (code) => {
      if (code === 0) resolve(undefined);
      else reject(new Error(`${command} ${args.join(" ")} failed with code ${code ?? "unknown"}`));
    });
    child.on("error", reject);
  });
}

async function hasValidLiveEndpoint() {
  const url = process.env.ATHENA_MANSERYEOK_API_URL?.trim();
  const token = process.env.ATHENA_MANSERYEOK_API_TOKEN?.trim();
  if (!url) return false;

  try {
    const parsed = new URL(url);
    if (!/^https?:$/.test(parsed.protocol)) return false;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
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
      if (!res.ok) return false;
      const json = await res.json().catch(() => null);
      return typeof json?.saju_label === "string" && json.saju_label.trim().length > 0;
    } finally {
      clearTimeout(timeout);
    }
  } catch {
    return false;
  }
}

async function main() {
  const useLive = await hasValidLiveEndpoint();
  if (useLive) {
    console.log("[verify:auto] live endpoint validated -> running verify:live");
    await run("npm", ["run", "verify:live"]);
    return;
  }
  console.log("[verify:auto] live endpoint unavailable -> running verify:full");
  await run("npm", ["run", "verify:full"]);
}

main().catch((error) => {
  console.error(`[verify:auto] ${error.message}`);
  process.exit(1);
});
