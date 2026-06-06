import fs from "node:fs";
import path from "node:path";

const MARKER = path.join("scripts", "build_han_physician_clinical_assist_turn_v1.py");

/** Resolve monorepo root for Python artifact chains. */
export function resolveMkmWorkspaceRoot(): string | null {
  const fromEnv = process.env.MKM_WORKSPACE_ROOT?.trim();
  if (fromEnv) {
    const abs = path.resolve(fromEnv);
    if (fs.existsSync(path.join(abs, MARKER))) return abs;
  }
  const cwd = process.cwd();
  const candidates = [
    cwd,
    path.resolve(cwd, ".."),
    path.resolve(cwd, "..", ".."),
    path.resolve(cwd, "..", "..", ".."),
  ];
  for (const root of candidates) {
    if (fs.existsSync(path.join(root, MARKER))) return root;
  }
  return null;
}
