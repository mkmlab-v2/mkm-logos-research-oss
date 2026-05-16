/**
 * Run monorepo `build_patient_care_bundle_from_km_cds_chain_v1.py` on a validated CDS envelope.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { resolveMkmWorkspaceRoot } from "./km-cds-envelope-python-bridge-v1";

export type BirthLocalParts = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
};

export type PatientCareBundleChainRequest = {
  requestId: string;
  cdsEnvelope: Record<string, unknown>;
  birth: BirthLocalParts;
  ianaTz: string;
  isMale?: boolean;
  soapJson?: Record<string, unknown>;
  applySlotTemplates?: boolean;
  validatePolicy?: boolean;
  validateBundle?: boolean;
  renderMdOut?: boolean;
};

export type PatientCareBundleChainResult =
  | {
      ok: true;
      bundlePath: string;
      myeongniPath: string;
      markdownPath?: string;
      bundle: Record<string, unknown>;
    }
  | { ok: false; error: string; stderr?: string };

/** Core CDS envelope for Python jsonschema (tri-layer is returned separately on API). */
export function prepareCdsEnvelopeForBundleChain(
  envelope: Record<string, unknown>,
): Record<string, unknown> {
  const { mkm_bianzheng_tri_layer: _tri, ...core } = envelope;
  return core;
}

export function birthInstantToLocalParts(utcIso: string, ianaTz: string): BirthLocalParts {
  const date = new Date(utcIso);
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: ianaTz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const parts = fmt.formatToParts(date);
  const pick = (type: string) => Number(parts.find((p) => p.type === type)?.value || "0");
  let hour = pick("hour");
  // ICU on some Linux hosts emits 24 at local midnight instead of 0.
  if (hour === 24) hour = 0;
  return {
    year: pick("year"),
    month: pick("month"),
    day: pick("day"),
    hour,
    minute: pick("minute"),
    second: pick("second"),
  };
}

export function runPatientCareBundleFromCdsChain(
  req: PatientCareBundleChainRequest,
  workspaceRoot?: string,
): PatientCareBundleChainResult {
  const root = workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) {
    return { ok: false, error: "MKM_WORKSPACE_ROOT not set or scripts missing" };
  }

  const chainScript = path.join(root, "scripts", "build_patient_care_bundle_from_km_cds_chain_v1.py");
  if (!fs.existsSync(chainScript)) {
    return { ok: false, error: `chain script not found: ${chainScript}` };
  }

  const runDir = path.join(root, "reports", "cdss_runtime", req.requestId.replace(/[^\w.-]+/g, "_"));
  fs.mkdirSync(runDir, { recursive: true });

  const envelopePath = path.join(runDir, "cds_envelope.json");
  const soapPath = path.join(runDir, "soap.json");
  const bundleOut = path.join(runDir, "patient_care_bundle.json");
  const myeongniOut = path.join(runDir, "myeongni_full.json");
  const mdOut = req.renderMdOut ? path.join(runDir, "patient_facing.md") : undefined;

  const envelopeForChain = prepareCdsEnvelopeForBundleChain(req.cdsEnvelope);
  fs.writeFileSync(envelopePath, `${JSON.stringify(envelopeForChain, null, 2)}\n`, "utf-8");
  if (req.soapJson) {
    fs.writeFileSync(soapPath, `${JSON.stringify(req.soapJson, null, 2)}\n`, "utf-8");
  }

  const py = process.env.MKM_PYTHON?.trim() || "py";
  const args = [
    chainScript,
    "--cds-envelope-json",
    envelopePath,
    "--local",
    String(req.birth.year),
    String(req.birth.month),
    String(req.birth.day),
    String(req.birth.hour),
    String(req.birth.minute),
    String(req.birth.second),
    "--iana-tz",
    req.ianaTz,
    "--myeongni-out",
    myeongniOut,
    "--bundle-out",
    bundleOut,
  ];

  if (req.soapJson) {
    args.push("--soap-json", soapPath);
  }
  if (req.isMale) args.push("--is-male");
  if (req.validateBundle) args.push("--validate-bundle");
  if (req.applySlotTemplates) args.push("--apply-slot-templates");
  if (req.validatePolicy) args.push("--validate-policy");
  if (req.validatePolicy) {
    args.push(
      "--policy-json",
      path.join(root, "docs", "final", "artifacts", "patient_care_bundle_generation_policy_v1.default.json"),
    );
  }
  if (mdOut) args.push("--render-md-out", mdOut);

  const child = spawnSync(py, args, {
    cwd: root,
    encoding: "utf-8",
    maxBuffer: 8 * 1024 * 1024,
    timeout: 120_000,
    windowsHide: true,
  });

  if (child.error) {
    return { ok: false, error: child.error.message, stderr: child.stderr };
  }
  if (child.status !== 0) {
    const err = (child.stderr || child.stdout || `exit ${child.status}`).trim();
    return { ok: false, error: err.slice(0, 3000), stderr: child.stderr };
  }

  if (!fs.existsSync(bundleOut)) {
    return { ok: false, error: `bundle output missing: ${bundleOut}`, stderr: child.stderr };
  }

  try {
    const bundle = JSON.parse(fs.readFileSync(bundleOut, "utf-8")) as Record<string, unknown>;
    if (bundle.schema !== "patient_care_bundle_v1") {
      return { ok: false, error: "bundle output schema is not patient_care_bundle_v1" };
    }
    return {
      ok: true,
      bundlePath: bundleOut,
      myeongniPath: myeongniOut,
      markdownPath: mdOut && fs.existsSync(mdOut) ? mdOut : undefined,
      bundle,
    };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return { ok: false, error: `failed to read bundle JSON: ${msg}` };
  }
}
