/**
 * Parallel push gate: infra closure + personadiary/smartfarm subroute smoke.
 */
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const root = join(scriptDir, "..");

const steps = [
  { id: "infra_closure", args: [join(scriptDir, "check-no1kmedi-infra-closure_v1.mjs")] },
  { id: "subroutes_smoke", args: [join(scriptDir, "check-no1kmedi-subroutes-smoke_v1.mjs")] },
];

let failed = null;
for (const step of steps) {
  console.log(`\n[check-no1kmedi-parallel-push_v1] === ${step.id} ===`);
  const code = spawnSync(process.execPath, step.args, { cwd: root, stdio: "inherit" }).status ?? 1;
  if (code !== 0) {
    failed = step.id;
    break;
  }
}

if (failed) {
  console.error(`\n[check-no1kmedi-parallel-push_v1] FAILED at ${failed}`);
  process.exit(1);
}
console.log("\n[check-no1kmedi-parallel-push_v1] all parallel lanes passed");
process.exit(0);
