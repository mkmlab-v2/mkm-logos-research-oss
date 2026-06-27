import fs from "node:fs";
import path from "node:path";

import {
  listPatientSlugsFromWorkspace,
  loadPatientPointer,
  type PatientSsotPointer,
} from "./clinician-patient-slug-v1";

/** Pointer `paths` keys surfaced in Human Gold v0 (SSOT contract). */
export const ENCOUNTER_ARTIFACT_MD_KEYS = [
  "lifestyle_management_md",
  "clinic_kakao",
  "patient_comprehensive_guide",
  "physician_comprehensive_guide",
] as const;

export type EncounterArtifactMdKey = (typeof ENCOUNTER_ARTIFACT_MD_KEYS)[number];

export type EncounterArtifactFileV1 = {
  key: string;
  rel_path: string;
  exists: boolean;
  content_type: "text/markdown" | "text/html" | "application/json";
  content?: string;
  truncated?: boolean;
  byte_length?: number;
};

export type EncounterArtifactsPayloadV1 = {
  success: true;
  slug: string;
  display_label: string;
  ref_token: string;
  rail: string;
  research_only: true;
  send_gate: "HOLD";
  management_mode?: Record<string, unknown>;
  paths: Record<string, string>;
  artifacts: EncounterArtifactFileV1[];
  print_html_rel: string | null;
  boundaries: string[];
  boundary_ko: string;
};

const MAX_MD_BYTES = 512_000;

function normDisplay(s: string): string {
  return s.replace(/\s+/g, "").trim();
}

export function resolveSlugFromDisplay(root: string, display: string): string | null {
  const target = normDisplay(display);
  if (!target) return null;
  for (const slug of listPatientSlugsFromWorkspace(root)) {
    const ptr = loadPatientPointer(root, slug);
    const label = normDisplay(String(ptr?.display_label || ""));
    if (label && label === target) return slug;
  }
  return null;
}

export function resolvePrintHtmlRel(paths: Record<string, string>): string | null {
  for (const [key, rel] of Object.entries(paths)) {
    if (!rel.endsWith(".html")) continue;
    if (rel.includes(" ") || rel.startsWith("py ")) continue;
    if (key.includes("print") || rel.includes("lifestyle_print")) return rel;
  }
  const cli = paths.lifestyle_render_cli || "";
  const m = /--out-html\s+(\S+)/.exec(cli);
  return m?.[1] || null;
}

function readTextArtifact(
  root: string,
  key: string,
  relPath: string,
  contentType: EncounterArtifactFileV1["content_type"],
  includeContent: boolean,
): EncounterArtifactFileV1 {
  const abs = path.join(root, relPath);
  const exists = fs.existsSync(abs);
  const base: EncounterArtifactFileV1 = {
    key,
    rel_path: relPath.replace(/\\/g, "/"),
    exists,
    content_type: contentType,
  };
  if (!exists || !includeContent) return base;

  const buf = fs.readFileSync(abs);
  base.byte_length = buf.length;
  if (buf.length > MAX_MD_BYTES) {
    base.content = buf.subarray(0, MAX_MD_BYTES).toString("utf-8");
    base.truncated = true;
    return base;
  }
  base.content = buf.toString("utf-8");
  return base;
}

export function loadEncounterArtifacts(args: {
  root: string;
  slug: string;
  pointer: PatientSsotPointer;
  includeContent?: boolean;
}): EncounterArtifactsPayloadV1 {
  const { root, slug, pointer } = args;
  const includeContent = args.includeContent !== false;
  const paths = pointer.paths || {};
  const artifacts: EncounterArtifactFileV1[] = [];

  for (const key of ENCOUNTER_ARTIFACT_MD_KEYS) {
    const rel = paths[key];
    if (!rel) continue;
    artifacts.push(readTextArtifact(root, key, rel, "text/markdown", includeContent));
  }

  const printRel = resolvePrintHtmlRel(paths);

  const boundaries = Array.isArray((pointer as { boundaries?: string[] }).boundaries)
    ? ((pointer as { boundaries?: string[] }).boundaries as string[])
    : [];

  return {
    success: true,
    slug,
    display_label: String(pointer.display_label || slug),
    ref_token: String(pointer.ref_token || ""),
    rail: "Track B",
    research_only: true,
    send_gate: "HOLD",
    management_mode: (pointer as { management_mode?: Record<string, unknown> }).management_mode,
    paths,
    artifacts,
    print_html_rel: printRel,
    boundaries,
    boundary_ko:
      "CDSS·교부물 초안. EMR 직접 기록 없음 — 복사·인쇄만. 최종 확정은 한의사(원장)만 수행합니다.",
  };
}

export function resolveEncounterPatient(args: {
  root: string;
  slug?: string;
  refToken?: string;
  display?: string;
}): { slug: string; pointer: PatientSsotPointer } | { error: string } {
  const explicit = (args.slug || "").trim();
  if (explicit) {
    const pointer = loadPatientPointer(args.root, explicit);
    if (!pointer) return { error: `unknown_slug:${explicit}` };
    return { slug: explicit, pointer };
  }

  const ref = (args.refToken || "").trim();
  if (ref) {
    for (const slug of listPatientSlugsFromWorkspace(args.root)) {
      const pointer = loadPatientPointer(args.root, slug);
      if (pointer?.ref_token === ref) return { slug, pointer };
    }
    return { error: `unknown_ref_token:${ref}` };
  }

  const display = (args.display || "").trim();
  if (display) {
    const slug = resolveSlugFromDisplay(args.root, display);
    if (!slug) return { error: `unknown_display:${display}` };
    const pointer = loadPatientPointer(args.root, slug);
    if (!pointer) return { error: `pointer_missing:${slug}` };
    return { slug, pointer };
  }

  return { error: "slug_ref_token_or_display_required" };
}

export function readEncounterPrintHtml(root: string, slug: string): { html: string } | { error: string } {
  const pointer = loadPatientPointer(root, slug);
  if (!pointer) return { error: `unknown_slug:${slug}` };
  const rel = resolvePrintHtmlRel(pointer.paths || {});
  if (!rel) return { error: "print_html_not_configured" };
  const abs = path.join(root, rel);
  if (!fs.existsSync(abs)) return { error: "print_html_missing_on_disk" };
  return { html: fs.readFileSync(abs, "utf-8") };
}
