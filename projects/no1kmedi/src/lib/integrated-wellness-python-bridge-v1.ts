/**
 * Run monorepo Integrated Wellness Solution v2 publish chain from consult or seed.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import type { PatientConsultInputV1 } from "./cdss-contract";
import { resolveMkmWorkspaceRoot } from "./km-cds-envelope-python-bridge-v1";

export type IntegratedWellnessChainRequest = {
  requestId: string;
  consult?: PatientConsultInputV1;
  sasangCandidate?: string;
  publishToNo1kmediPublic?: boolean;
  publishToPersonadiaryPublic?: boolean;
  publishToMkmlifePublic?: boolean;
};

export type IntegratedWellnessChainResult =
  | {
      ok: true;
      outDir: string;
      resolvedPath: string;
      no1kmediRenderPath: string;
      personadiaryPackagePath: string;
      mkmlifeRenderPath?: string;
      mkmlifeRender?: Record<string, unknown>;
      mkmlifeMarkdownPath?: string;
      manifest: Record<string, unknown>;
      no1kmediDraft?: Record<string, unknown>;
    }
  | { ok: false; error: string; stderr?: string };

const SASANG_NORMALIZE: Record<string, string> = {
  taeyang: "taeyang",
  soyag: "soyang",
  soyang: "soyang",
  taeeum: "taeum",
  taeum: "taeum",
  soeum: "soeum",
  unknown: "unknown",
};

export function runIntegratedWellnessPublishChain(
  req: IntegratedWellnessChainRequest,
  workspaceRoot?: string,
): IntegratedWellnessChainResult {
  const root = workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) {
    return { ok: false, error: "MKM_WORKSPACE_ROOT not set or scripts missing" };
  }

  const publishScript = path.join(root, "scripts", "publish_integrated_wellness_solution_v2_exports_v1.py");
  if (!fs.existsSync(publishScript)) {
    return { ok: false, error: `publish script not found: ${publishScript}` };
  }

  const runDir = path.join(
    root,
    "reports",
    "cdss_runtime",
    `iws_v2_${req.requestId.replace(/[^\w.-]+/g, "_")}`,
  );
  fs.mkdirSync(runDir, { recursive: true });

  const py =
    process.env.MKM_PYTHON?.trim() ||
    (process.platform === "win32" ? "py" : "python3");
  const args = [publishScript, "--out-dir", runDir];

  if (req.consult) {
    const consultPath = path.join(runDir, "patient_consult.json");
    const consultPayload = {
      ...req.consult,
      sasang_internal: SASANG_NORMALIZE[(req.sasangCandidate || "unknown").toLowerCase()] || "unknown",
    };
    fs.writeFileSync(consultPath, `${JSON.stringify(consultPayload, null, 2)}\n`, "utf-8");
    args.push("--consult-json", consultPath);
  } else {
    const defaultSeed = path.join(
      root,
      "docs",
      "final",
      "artifacts",
      "fixtures",
      "integrated_wellness_solution_v2_minor_soeum_abdomen_seed.example.json",
    );
    if (!fs.existsSync(defaultSeed)) {
      return { ok: false, error: `default seed missing: ${defaultSeed}` };
    }
    args.push("--seed-json", defaultSeed);
  }

  const no1kmediPublic = path.join(root, "projects", "no1kmedi", "public", "data", "integrated_wellness");
  const personadiaryPublic = path.join(root, "projects", "no1kmedi", "public", "data");

  if (req.publishToNo1kmediPublic !== false) {
    args.push("--no1kmedi-public", no1kmediPublic);
  }
  if (req.publishToPersonadiaryPublic !== false) {
    args.push("--personadiary-public", personadiaryPublic);
  }

  const mkmlifePublic = path.join(
    root,
    "projects",
    "mkm",
    "mkm-life",
    "public",
    "data",
  );
  if (req.publishToMkmlifePublic === true) {
    args.push("--mkmlife-public", mkmlifePublic);
  }

  const child = spawnSync(py, args, {
    cwd: root,
    encoding: "utf-8",
    maxBuffer: 8 * 1024 * 1024,
    timeout: 60_000,
    windowsHide: true,
  });

  if (child.error) {
    return { ok: false, error: child.error.message };
  }
  if (child.status !== 0) {
    return {
      ok: false,
      error: (child.stderr || child.stdout || `exit ${child.status}`).trim(),
      stderr: child.stderr || undefined,
    };
  }

  const manifestPath = path.join(runDir, "publish_manifest_latest.json");
  if (!fs.existsSync(manifestPath)) {
    return { ok: false, error: `manifest missing: ${manifestPath}`, stderr: child.stderr || undefined };
  }

  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8")) as Record<string, unknown>;
  const no1kmediRenderPath = path.join(runDir, "render_no1kmedi_latest.json");
  const resolvedPath = path.join(runDir, "resolved_latest.json");
  const personadiaryPackagePath = path.join(runDir, "personadiary_daily_package_latest.json");
  const mkmlifeRenderPath = path.join(runDir, "render_mkmlife_latest.json");
  const mkmlifeMarkdownPath = path.join(runDir, "mkmlife_report_latest.md");

  let no1kmediDraft: Record<string, unknown> | undefined;
  if (fs.existsSync(no1kmediRenderPath)) {
    no1kmediDraft = JSON.parse(fs.readFileSync(no1kmediRenderPath, "utf-8")) as Record<string, unknown>;
  }

  let mkmlifeRender: Record<string, unknown> | undefined;
  if (fs.existsSync(mkmlifeRenderPath)) {
    mkmlifeRender = JSON.parse(fs.readFileSync(mkmlifeRenderPath, "utf-8")) as Record<string, unknown>;
  }

  return {
    ok: true,
    outDir: runDir,
    resolvedPath,
    no1kmediRenderPath,
    personadiaryPackagePath,
    mkmlifeRenderPath: fs.existsSync(mkmlifeRenderPath) ? mkmlifeRenderPath : undefined,
    mkmlifeRender,
    mkmlifeMarkdownPath: fs.existsSync(mkmlifeMarkdownPath) ? mkmlifeMarkdownPath : undefined,
    manifest,
    no1kmediDraft,
  };
}
