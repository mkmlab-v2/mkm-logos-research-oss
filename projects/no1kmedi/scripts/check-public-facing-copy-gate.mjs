#!/usr/bin/env node
/** Run monorepo combination fingerprint gate from no1kmedi package scripts. */

import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..", "..");
const gateScript = path.join(repoRoot, "scripts", "check_public_facing_copy_gate_v1.py");

function resolvePython() {
  for (const cmd of ["py", "python3", "python"]) {
    const probe = spawnSync(cmd, ["--version"], { encoding: "utf8" });
    if (probe.status === 0) return cmd;
  }
  return "python3";
}

const python = resolvePython();
const result = spawnSync(python, [gateScript], {
  cwd: repoRoot,
  encoding: "utf8",
  stdio: "inherit",
});

if (result.error) {
  console.error("[check-public-facing-copy-gate] failed to spawn python:", result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
