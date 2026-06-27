import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { resolveMkmWorkspaceRoot } from "./km-workspace-root-v1";

export type EncounterSequenceChainRequest = {
  slug: string;
};

export type EncounterSequenceChainResult =
  | {
      ok: true;
      slug: string;
      refToken: string | null;
      encounterSequenceId: string | null;
      sequencePath: string;
      bundlePath: string;
      hanTurnPath: string;
      l0RouterTriggered: boolean | null;
    }
  | { ok: false; error: string; stderr?: string };

function parseStdoutJson(stdout: string): Record<string, unknown> | null {
  const lines = stdout.trim().split(/\r?\n/).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    try {
      return JSON.parse(lines[i]!) as Record<string, unknown>;
    } catch {
      /* continue */
    }
  }
  return null;
}

export function runEncounterSequenceClinicianChain(
  req: EncounterSequenceChainRequest,
  workspaceRoot?: string,
): EncounterSequenceChainResult {
  const root = workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) {
    return { ok: false, error: "MKM_WORKSPACE_ROOT not set or han_physician builder missing" };
  }

  const slug = req.slug.trim();
  if (!slug) return { ok: false, error: "missing_slug" };

  const script = path.join(root, "scripts", "run_encounter_sequence_clinician_api_chain_v1.py");
  if (!fs.existsSync(script)) {
    return { ok: false, error: "encounter_sequence clinician chain script missing" };
  }

  const py = process.env.MKM_PYTHON?.trim() || "py";
  const child = spawnSync(py, [script, "--slug", slug], {
    cwd: root,
    encoding: "utf-8",
    maxBuffer: 8 * 1024 * 1024,
    timeout: 120_000,
    windowsHide: true,
  });

  if (child.status !== 0) {
    return {
      ok: false,
      error: (child.stderr || child.stdout || `chain exit ${child.status}`).trim().slice(0, 3000),
      stderr: child.stderr,
    };
  }

  const smokePath = path.join(root, "reports", "encounter_sequence_clinician_api_e2e_smoke_v1_latest.json");
  if (!fs.existsSync(smokePath)) {
    return { ok: false, error: `smoke artifact missing: ${smokePath}` };
  }

  const smoke = JSON.parse(fs.readFileSync(smokePath, "utf-8")) as {
    smoke_ok?: boolean;
    ref_token?: string;
    encounter_sequence_id?: string;
    sequence_path?: string;
    bundle_path?: string;
    han_turn_path?: string;
    l0_router_triggered?: boolean;
  };

  if (!smoke.smoke_ok) {
    return { ok: false, error: "encounter_sequence_clinician_api_smoke_not_ok" };
  }

  return {
    ok: true,
    slug,
    refToken: smoke.ref_token || null,
    encounterSequenceId: smoke.encounter_sequence_id || null,
    sequencePath: smoke.sequence_path || "",
    bundlePath: smoke.bundle_path || "",
    hanTurnPath: smoke.han_turn_path || "",
    l0RouterTriggered: smoke.l0_router_triggered ?? null,
  };
}
