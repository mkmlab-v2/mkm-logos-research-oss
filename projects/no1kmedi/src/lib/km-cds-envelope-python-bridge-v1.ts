/**
 * Optional Fact-Lock validation: run monorepo Python builder on adapter payload.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import type { KmPhysicianCdsPayloadV1 } from "./km-cds-envelope-adapter-v1";

export type KmCdsEnvelopeValidationResult =
  | { ok: true; envelope: Record<string, unknown>; method: "python" }
  | { ok: false; error: string; method: "python" | "skipped" };

export function resolveMkmWorkspaceRoot(): string | null {
  const fromEnv = process.env.MKM_WORKSPACE_ROOT?.trim();
  if (fromEnv && fs.existsSync(path.join(fromEnv, "scripts", "build_km_physician_cds_assist_envelope_v1.py"))) {
    return fromEnv;
  }
  return null;
}

export function shouldValidateKmCdsEnvelopeViaPython(): boolean {
  if (process.env.KM_CDS_ENVELOPE_VALIDATE?.trim() === "1") return true;
  if (process.env.KM_CDS_ENVELOPE_VALIDATE?.trim() === "0") return false;
  return Boolean(resolveMkmWorkspaceRoot());
}

/**
 * Invoke `py scripts/build_km_physician_cds_assist_envelope_v1.py` with payload on stdin.
 */
export function validateKmCdsPayloadWithPython(
  payload: KmPhysicianCdsPayloadV1,
  workspaceRoot?: string,
): KmCdsEnvelopeValidationResult {
  const root = workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) {
    return { ok: false, error: "MKM_WORKSPACE_ROOT not set or builder script missing", method: "skipped" };
  }

  const scriptPath = path.join(root, "scripts", "build_km_physician_cds_assist_envelope_v1.py");
  if (!fs.existsSync(scriptPath)) {
    return { ok: false, error: `builder not found: ${scriptPath}`, method: "skipped" };
  }

  const py = process.env.MKM_PYTHON?.trim() || "py";
  const child = spawnSync(py, [scriptPath, "--input-json", "-"], {
    cwd: root,
    input: JSON.stringify(payload),
    encoding: "utf-8",
    maxBuffer: 4 * 1024 * 1024,
    timeout: 20_000,
    windowsHide: true,
  });

  if (child.error) {
    return { ok: false, error: child.error.message, method: "python" };
  }
  if (child.status !== 0) {
    const err = (child.stderr || child.stdout || `exit ${child.status}`).trim();
    return { ok: false, error: err.slice(0, 2000), method: "python" };
  }

  try {
    const envelope = JSON.parse(child.stdout) as Record<string, unknown>;
    if (envelope.schema !== "km_physician_cds_assist_envelope_v1") {
      return { ok: false, error: "builder output missing km_physician_cds_assist_envelope_v1 schema", method: "python" };
    }
    return { ok: true, envelope, method: "python" };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return { ok: false, error: `invalid builder JSON: ${msg}`, method: "python" };
  }
}
