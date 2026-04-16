#!/usr/bin/env node
import { spawn } from "node:child_process";

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
  if (!url) return false;

  try {
    const parsed = new URL(url);
    if (!/^https?:$/.test(parsed.protocol)) return false;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ birth_datetime: "1990-01-01 00:00" }),
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
    console.log("[recommended-gate] live endpoint validated -> running live gate");
    await run("npm", ["run", "smoke:commercialization-gate:live"]);
    return;
  }
  console.log("[recommended-gate] live endpoint unavailable -> running standard gate");
  await run("npm", ["run", "smoke:commercialization-gate"]);
}

main().catch((error) => {
  console.error(`[recommended-gate] ${error.message}`);
  process.exit(1);
});
