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

const dbUrl = (process.env.NO1KMEDI_POSTGRES_URL || process.env.DATABASE_URL || "").trim();
if (!dbUrl) {
  console.error(
    "[verify:postgres] NO1KMEDI_POSTGRES_URL (or DATABASE_URL) is required for postgres verification.",
  );
  process.exit(1);
}

function run(command, args, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: "inherit",
      shell: process.platform === "win32",
      env,
    });
    child.on("exit", (code) => {
      if (code === 0) resolve(undefined);
      else reject(new Error(`${command} ${args.join(" ")} failed with code ${code ?? "unknown"}`));
    });
    child.on("error", reject);
  });
}

const env = {
  ...process.env,
  NO1KMEDI_STORE_DRIVER: "postgres",
  NO1KMEDI_POSTGRES_URL: dbUrl,
};

run("npm", ["run", "verify:auto"], env).catch((error) => {
  console.error(`[verify:postgres] ${error.message}`);
  process.exit(1);
});

