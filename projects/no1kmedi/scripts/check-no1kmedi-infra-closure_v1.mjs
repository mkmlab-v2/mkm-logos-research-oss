/**
 * One-shot infra closure: VPS PM2 probe → staging preflight → deploy readiness.
 * Run from projects/no1kmedi: node scripts/check-no1kmedi-infra-closure_v1.mjs
 */
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const root = join(scriptDir, "..");
const repoRoot = join(root, "../..");

function run(cmd, args, cwd) {
  const r = spawnSync(cmd, args, { cwd, stdio: "inherit", shell: process.platform === "win32" });
  return r.status ?? 1;
}

const steps = [
  {
    id: "vps_pm2",
    cmd: "powershell",
    args: [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      join(repoRoot, "scripts", "Invoke-No1kmediVpsPm2Preflight_v1.ps1"),
    ],
    cwd: repoRoot,
  },
  {
    id: "staging_preflight",
    cmd: "node",
    args: [join(scriptDir, "check-no1kmedi-staging-preflight_v1.mjs")],
    cwd: root,
  },
  {
    id: "deploy_readiness",
    cmd: "node",
    args: [join(scriptDir, "check-no1kmedi-deploy-readiness_v1.mjs")],
    cwd: root,
  },
];

let failed = null;
for (const step of steps) {
  console.log(`\n[check-no1kmedi-infra-closure_v1] === ${step.id} ===`);
  const code = run(step.cmd, step.args, step.cwd);
  if (code !== 0) {
    failed = step.id;
    break;
  }
}

if (failed) {
  console.error(`\n[check-no1kmedi-infra-closure_v1] FAILED at step: ${failed}`);
  process.exit(1);
}
console.log("\n[check-no1kmedi-infra-closure_v1] all steps passed");
process.exit(0);
