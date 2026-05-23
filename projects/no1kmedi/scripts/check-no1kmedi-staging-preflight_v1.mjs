/**
 * Local staging preflight for no1kmedi (no deploy, no push).
 * Run from projects/no1kmedi: node scripts/check-no1kmedi-staging-preflight_v1.mjs
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(root, "../..");

const ssot = {
  doc: "docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md",
  topology: "docs/final/MKM_HOSTINGER_CLOUDFLARE_TOPOLOGY_V1.md",
  design_fusion: "docs/final/artifacts/no1kmedi_design_fusion_ssot_v1.json",
  pm2_no1kmedi_com_doc: "/opt/no1kmedi-com/.next/standalone",
  pm2_no1kmedi_com_tarball: "/opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi",
  pm2_mkmlife: "/var/www/mkmlife_runtime/mkm-life",
  deploy_tarball_script: "scripts/Deploy-No1kmediDestinyTarball_v1.ps1",
  vps_pm2_probe_script: "scripts/Invoke-No1kmediVpsPm2Preflight_v1.ps1",
  nginx_api_snippet: "scripts/deploy/linux/nginx-api.no1kmedi.com.snippet.conf",
};

const report = {
  schema: "no1kmedi_staging_preflight_v1",
  generated_at_utc: new Date().toISOString(),
  deploy_triggered: false,
  git_push: false,
  ssot_pointers: ssot,
  local: {},
  remote_probe: {},
  remote_content_markers: {},
  design_fusion: {},
  infra_closure: {},
  checklist_for_human_vps_ssh: [
    "pm2 describe no1kmedi-com — exec cwd expected: /opt/mkm-destiny-ai-41e38ec6/projects/no1kmedi (tarball; not standalone)",
    "pm2 describe mkmlife — exec cwd expected: /var/www/mkmlife_runtime/mkm-life",
    "curl -sS https://api.no1kmedi.com/health — expect ok:true",
    "on VPS: nginx -t && curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3010/ — expect 200",
    "automated probe: scripts/Invoke-No1kmediVpsPm2Preflight_v1.ps1 → reports/no1kmedi_vps_pm2_preflight_latest.json",
  ],
};

function fileOk(relFromRepo) {
  const p = join(repoRoot, relFromRepo.replace(/\//g, "\\"));
  const ok = existsSync(p);
  return { path: relFromRepo, exists: ok };
}

report.local.build_artifact = {
  next_dir: existsSync(join(root, ".next")),
  next_build_id: existsSync(join(root, ".next", "BUILD_ID")),
  standalone_dir: existsSync(join(root, ".next", "standalone")),
};

for (const key of ["doc", "topology", "nginx_api_snippet", "design_fusion"]) {
  report.local[key] = fileOk(ssot[key]);
}

try {
  const pkg = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));
  report.local.package_name = pkg.name;
  report.local.has_build_script = typeof pkg.scripts?.build === "string";
} catch (e) {
  report.local.package_error = String(e);
}

let expectedHeroPrimary = "상담 전 참고 리포트 시작";
try {
  const copy = JSON.parse(readFileSync(join(root, "marketing-site", "public-copy.json"), "utf8"));
  expectedHeroPrimary = copy?.hero?.cta_primary ?? expectedHeroPrimary;
} catch {
  /* use default */
}

try {
  const fusion = JSON.parse(readFileSync(join(repoRoot, ssot.design_fusion), "utf8"));
  report.design_fusion = {
    layer_a_status: fusion.layer_a_status,
    layer_b_status: fusion.layer_b_status,
    layer_b_deferred_ok: fusion.layer_b_status === "deferred_code_first",
    layer_b_policy: fusion.layer_b_policy ?? null,
  };
} catch (e) {
  report.design_fusion = { error: String(e) };
}

const urls = [
  { id: "jema_ai_home", url: "https://jema-ai.com/" },
  { id: "app_jema_ai", url: "https://app.jema-ai.com/" },
  { id: "app_enterprise", url: "https://app.jema-ai.com/enterprise" },
  { id: "app_clinician", url: "https://app.jema-ai.com/clinician" },
  { id: "api_health", url: "https://api.no1kmedi.com/health" },
];

for (const { id, url } of urls) {
  try {
    const res = await fetch(url, { method: "GET", redirect: "follow", signal: AbortSignal.timeout(12000) });
    const body = await res.text();
    report.remote_probe[id] = {
      url,
      status: res.status,
      ok: res.ok,
      content_type: res.headers.get("content-type"),
      body_snippet: body.slice(0, 120).replace(/\s+/g, " "),
    };
    if (id === "jema_ai_home") {
      report.remote_content_markers.hero_cta_primary = body.includes(expectedHeroPrimary);
      report.remote_content_markers.governance_flow_anchor = body.includes("governance-flow");
      report.remote_content_markers.design_token_class = body.includes("hero-") || body.includes("MKM-DESIGN");
    }
    if (id === "api_health") {
      report.remote_content_markers.api_ok_true = body.includes('"ok":true') || body.includes('"ok": true');
    }
  } catch (e) {
    report.remote_probe[id] = { url, error: String(e) };
  }
}

const vpsReportPath = join(repoRoot, "reports", "no1kmedi_vps_pm2_preflight_latest.json");
if (existsSync(vpsReportPath)) {
  try {
    report.vps_pm2_preflight = JSON.parse(readFileSync(vpsReportPath, "utf8"));
  } catch (e) {
    report.vps_pm2_preflight = { error: String(e) };
  }
} else {
  report.vps_pm2_preflight = { missing: true, path: "reports/no1kmedi_vps_pm2_preflight_latest.json" };
}

const vps = report.vps_pm2_preflight;
const vpsOk =
  !vps?.missing &&
  vps?.ssh_success === true &&
  vps?.pm2_facts?.["no1kmedi-com"]?.status === "online" &&
  vps?.ssot_reconciliation?.vps_no1kmedi_uses_tarball_path === true &&
  (vps?.origin_probe?.local_next_3010_status === 200);

const remoteOk = Object.values(report.remote_probe).every((p) => p.ok === true);
const markersOk =
  report.remote_content_markers.hero_cta_primary === true &&
  report.remote_content_markers.api_ok_true === true;
const fusionOk = report.design_fusion?.layer_b_deferred_ok === true;

report.infra_closure = {
  local_build_ready: Boolean(report.local.build_artifact?.next_build_id && report.local.has_build_script),
  remote_edge_ok: remoteOk,
  live_copy_markers_ok: markersOk,
  layer_b_not_blocking: fusionOk,
  vps_pm2_ok: vpsOk,
  vps_pm2_stale: Boolean(vps?.missing),
  nginx_origin_note: "api.no1kmedi.com snippet SSOT on disk; jema-ai.com edge via Cloudflare → nginx → :3010",
  closure_ok: false,
};

report.infra_closure.closure_ok =
  report.infra_closure.local_build_ready &&
  report.infra_closure.remote_edge_ok &&
  report.infra_closure.live_copy_markers_ok &&
  report.infra_closure.layer_b_not_blocking &&
  (vpsOk || vps?.missing);

const outPath = join(repoRoot, "reports", "no1kmedi_staging_preflight_latest.json");
mkdirSync(join(repoRoot, "reports"), { recursive: true });
writeFileSync(outPath, JSON.stringify(report, null, 2), "utf8");

console.log(JSON.stringify(report, null, 2));
console.log(`\n[check-no1kmedi-staging-preflight_v1] wrote ${outPath}`);
console.log(
  `[check-no1kmedi-staging-preflight_v1] infra_closure.closure_ok=${report.infra_closure.closure_ok}`,
);
process.exit(report.infra_closure.closure_ok ? 0 : 1);
