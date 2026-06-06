import fs from "node:fs";
import path from "node:path";

import { resolveMkmWorkspaceRoot } from "./km-workspace-root-v1";

export type PatientSsotPointer = {
  schema?: string;
  display_label?: string;
  ref_token?: string;
  paths?: Record<string, string>;
};

export function listPatientSlugsFromWorkspace(root: string): string[] {
  const reports = path.join(root, "reports");
  if (!fs.existsSync(reports)) return [];
  const slugs = new Set<string>();
  for (const name of fs.readdirSync(reports)) {
    const m = /^(.+)_intake_ssot_pointer_v1\.json$/.exec(name);
    if (m?.[1]) slugs.add(m[1]);
  }
  return [...slugs].sort();
}

export function loadPatientPointer(root: string, slug: string): PatientSsotPointer | null {
  const p = path.join(root, "reports", `${slug}_intake_ssot_pointer_v1.json`);
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, "utf-8")) as PatientSsotPointer;
  } catch {
    return null;
  }
}

export function resolveSlugFromRefToken(root: string, refToken: string): string | null {
  const token = refToken.trim();
  if (!token) return null;
  for (const slug of listPatientSlugsFromWorkspace(root)) {
    const ptr = loadPatientPointer(root, slug);
    if (ptr?.ref_token === token) return slug;
  }
  return null;
}

export function resolvePatientSlug(input: {
  slug?: string;
  refToken?: string;
  workspaceRoot?: string;
}): { slug: string; pointer: PatientSsotPointer } | { error: string } {
  const root = input.workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) return { error: "workspace_root_not_found" };

  const explicit = (input.slug || "").trim();
  if (explicit) {
    const pointer = loadPatientPointer(root, explicit);
    if (!pointer) return { error: `unknown_slug:${explicit}` };
    return { slug: explicit, pointer };
  }

  const fromRef = input.refToken ? resolveSlugFromRefToken(root, input.refToken) : null;
  if (fromRef) {
    const pointer = loadPatientPointer(root, fromRef);
    if (!pointer) return { error: `pointer_missing:${fromRef}` };
    return { slug: fromRef, pointer };
  }

  return { error: "slug_or_ref_token_required" };
}
