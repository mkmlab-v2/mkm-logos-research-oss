/**
 * Pre-deploy gate for no1kmedi tarball (no deploy, no push).
 * Run: npm run check:deploy-readiness
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(root, "../..");

const report = {
  schema: "no1kmedi_deploy_readiness_v1",
  generated_at_utc: new Date().toISOString(),
  deploy_triggered: false,
  git_push: false,
  ready: false,
  checks: {},
  deploy_command: "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Deploy-No1kmediDestinyTarball_v1.ps1 -DryRun",
  deploy_command_live:
    "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Deploy-No1kmediDestinyTarball_v1.ps1",
  blockers: [],
};

function addCheck(id, ok, detail) {
  report.checks[id] = { ok, detail };
  if (!ok) report.blockers.push(`${id}: ${detail}`);
}

addCheck("next_build_id", existsSync(join(root, ".next", "BUILD_ID")), "run npm run build first");

const designSmoke = spawnSync(process.execPath, ["./scripts/check-design-tokens-smoke.mjs"], {
  cwd: root,
  encoding: "utf8",
});
addCheck(
  "design_tokens_smoke",
  designSmoke.status === 0,
  designSmoke.status === 0 ? "passed" : (designSmoke.stderr || designSmoke.stdout || "").slice(0, 400)
);

const stagingPath = join(repoRoot, "reports", "no1kmedi_staging_preflight_latest.json");
if (existsSync(stagingPath)) {
  try {
    const staging = JSON.parse(readFileSync(stagingPath, "utf8"));
    const remoteOk =
      staging.remote_probe?.jema_ai_home?.ok &&
      staging.remote_probe?.api_health?.ok;
    addCheck("staging_remote_probe", !!remoteOk, remoteOk ? "jema-ai + api health ok" : "re-run check:staging-preflight");
    const vps = staging.vps_pm2_preflight;
    const vpsOk =
      vps?.ssh_success &&
      vps?.ssot_reconciliation?.vps_no1kmedi_uses_tarball_path === true;
    addCheck(
      "vps_pm2_tarball_path",
      !!vpsOk,
      vpsOk
        ? `exec cwd ${vps?.pm2_facts?.["no1kmedi-com"]?.exec_cwd ?? "ok"}`
        : "run npm run check:staging-vps-pm2 from projects/no1kmedi",
    );
    addCheck(
      "infra_closure",
      staging.infra_closure?.closure_ok === true,
      staging.infra_closure?.closure_ok
        ? "staging preflight infra_closure ok"
        : "re-run npm run check:infra-closure",
    );
  } catch (e) {
    addCheck("staging_json", false, String(e));
  }
} else {
  addCheck("staging_json", false, "missing reports/no1kmedi_staging_preflight_latest.json");
}

const figmaUrl = process.env.FIGMA_TARGET_DESIGN_URL?.trim();
addCheck(
  "layer_b_figma",
  true,
  figmaUrl
    ? "FIGMA_TARGET_DESIGN_URL set (optional Figma sync available)"
    : "Layer B deferred_code_first — code-first SSOT; Figma Design URL not required for deploy"
);

report.ready = report.blockers.length === 0;

const outPath = join(repoRoot, "reports", "no1kmedi_deploy_readiness_latest.json");
mkdirSync(join(repoRoot, "reports"), { recursive: true });
writeFileSync(outPath, JSON.stringify(report, null, 2), "utf8");

console.log(JSON.stringify(report, null, 2));
console.log(`\n[check-no1kmedi-deploy-readiness_v1] wrote ${outPath}`);
process.exit(report.ready ? 0 : 1);
