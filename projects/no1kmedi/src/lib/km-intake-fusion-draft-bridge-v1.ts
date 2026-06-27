import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { resolveEncounterPatient } from "@/lib/clinician-encounter-artifacts-v1";
import { parseIntakePasteText } from "@/lib/clinician-intake-paste-v1";
import { loadPatientPointer, type PatientSsotPointer } from "@/lib/clinician-patient-slug-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export type IntakeFusionDraftRequestV1 = {
  slug?: string;
  refToken?: string;
  display?: string;
  intakeText: string;
  objectiveDraft?: string;
  birthInstantUtc?: string;
  ianaTz?: string;
  isMale?: boolean;
  sasangLabel?: string;
  validateSchema?: boolean;
  validatePolicy?: boolean;
  renderMd?: boolean;
  briefOutput?: boolean;
};

export type IntakeFusionDraftResultV1 =
  | {
      ok: true;
      slug: string;
      refToken: string;
      displayLabel: string;
      bundlePath: string;
      myeongniPath: string;
      rationalePath: string;
      markdownPath?: string;
      bundle: Record<string, unknown>;
      patientFacingMarkdown?: string;
      soap: Record<string, { text?: string }>;
    }
  | { ok: false; error: string; stderr?: string };

type TrackBMemoryProfile = {
  birth_local?: string;
  sex?: string;
};

function birthLocalToUtcInstant(birthLocal: string): string | null {
  const d = new Date(birthLocal);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function loadTrackBProfile(root: string, pointer: PatientSsotPointer): {
  birth_instant_utc: string;
  iana_tz: string;
  is_male: boolean;
} | null {
  const rel = pointer.paths?.patient_track_b_memory;
  if (!rel) return null;
  const abs = path.join(root, rel);
  if (!fs.existsSync(abs)) return null;
  try {
    const doc = JSON.parse(fs.readFileSync(abs, "utf-8")) as {
      profile?: TrackBMemoryProfile;
    };
    const p = doc.profile;
    if (!p?.birth_local) return null;
    const birthInstant = birthLocalToUtcInstant(p.birth_local);
    if (!birthInstant) return null;
    return {
      birth_instant_utc: birthInstant,
      iana_tz: "Asia/Seoul",
      is_male: p.sex === "male",
    };
  } catch {
    return null;
  }
}

function loadBaseIntakeDoc(root: string, pointer: PatientSsotPointer): Record<string, unknown> | null {
  const rel = pointer.paths?.intake;
  if (!rel) return null;
  const abs = path.join(root, rel);
  if (!fs.existsSync(abs)) return null;
  try {
    return JSON.parse(fs.readFileSync(abs, "utf-8")) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export type EncounterBirthProfileV1 = {
  birth_instant_utc: string;
  iana_tz: string;
  is_male: boolean;
};

export function resolveEncounterBirthProfile(
  root: string,
  pointer: PatientSsotPointer,
  req: Pick<IntakeFusionDraftRequestV1, "birthInstantUtc" | "ianaTz" | "isMale">,
): EncounterBirthProfileV1 | null {
  const explicitUtc = req.birthInstantUtc?.trim();
  if (explicitUtc) {
    return {
      birth_instant_utc: explicitUtc,
      iana_tz: req.ianaTz?.trim() || "Asia/Seoul",
      is_male: Boolean(req.isMale),
    };
  }
  const fromTrackB = loadTrackBProfile(root, pointer);
  if (fromTrackB) return fromTrackB;
  const base = loadBaseIntakeDoc(root, pointer);
  const profile = base?.profile;
  if (profile && typeof profile === "object") {
    const p = profile as Record<string, unknown>;
    const biu = String(p.birth_instant_utc || "").trim();
    if (biu) {
      return {
        birth_instant_utc: biu,
        iana_tz: String(p.iana_tz || "Asia/Seoul"),
        is_male: Boolean(p.is_male),
      };
    }
  }
  return null;
}

export function buildIntakeFusionDraftInput(args: {
  root: string;
  slug: string;
  pointer: PatientSsotPointer;
  req: IntakeFusionDraftRequestV1;
}): { doc: Record<string, unknown> } | { error: string } {
  const { root, slug, pointer, req } = args;
  const paste = parseIntakePasteText(req.intakeText);
  if (!paste.subjective_notes.trim()) {
    return { error: "intake_text_required" };
  }

  const birth = resolveEncounterBirthProfile(root, pointer, req);
  if (!birth) {
    return {
      error: "birth_profile_missing: provide birth_instant_utc or complete patient_track_b_memory / paths.intake",
    };
  }

  const refToken = String(pointer.ref_token || slug).trim();
  const base = loadBaseIntakeDoc(root, pointer);
  const priorIntake =
    base?.intake && typeof base.intake === "object" ? (base.intake as Record<string, unknown>) : {};

  const sasangFromBase =
    priorIntake.sasang_estimate && typeof priorIntake.sasang_estimate === "object"
      ? (priorIntake.sasang_estimate as Record<string, unknown>)
      : {};

  const doc: Record<string, unknown> = base
    ? {
        ...base,
        encounter: { ref_token: refToken },
        profile: birth,
      }
    : {
        schema: "patient_intake_fusion_draft_v1",
        version: "1.0.0",
        encounter: { ref_token: refToken },
        profile: birth,
        options: {
          include_logos_symbolic: true,
          apply_slot_templates_fill_empty_only: true,
        },
      };

  doc.intake = {
    ...priorIntake,
    symptoms: paste.symptoms.length ? paste.symptoms : priorIntake.symptoms || [],
    situation: paste.situation || priorIntake.situation || "",
    subjective_notes: paste.subjective_notes,
    ...(req.objectiveDraft?.trim()
      ? { objective_draft: req.objectiveDraft.trim().slice(0, 12000) }
      : priorIntake.objective_draft
        ? { objective_draft: priorIntake.objective_draft }
        : {}),
    sasang_estimate: {
      label: req.sasangLabel?.trim() || String(sasangFromBase.label || "미입력"),
      source: req.sasangLabel?.trim() ? "clinician_paste_v1" : String(sasangFromBase.source || "ssot_base"),
    },
  };

  doc.meta = {
    ...(typeof doc.meta === "object" && doc.meta ? (doc.meta as Record<string, unknown>) : {}),
    intake_paste_generated_at_utc: new Date().toISOString(),
    slug,
    phi_minimal: true,
  };

  return { doc };
}

export function runIntakeFusionDraftChain(
  req: IntakeFusionDraftRequestV1,
  workspaceRoot?: string,
): IntakeFusionDraftResultV1 {
  const root = workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_not_found" };

  const resolved = resolveEncounterPatient({
    root,
    slug: req.slug,
    refToken: req.refToken,
    display: req.display,
  });
  if ("error" in resolved) return { ok: false, error: resolved.error };

  const built = buildIntakeFusionDraftInput({
    root,
    slug: resolved.slug,
    pointer: resolved.pointer,
    req,
  });
  if ("error" in built) return { ok: false, error: built.error };

  const script = path.join(root, "scripts", "build_patient_intake_fusion_draft_v1.py");
  if (!fs.existsSync(script)) return { ok: false, error: "build_patient_intake_fusion_draft_v1.py missing" };

  const runId = `${resolved.slug}_${Date.now()}`;
  const runDir = path.join(root, "reports", "cdss_runtime", `intake_fusion_${runId}`);
  fs.mkdirSync(runDir, { recursive: true });

  const intakePath = path.join(runDir, "intake.json");
  const bundleOut = path.join(runDir, "bundle.json");
  const myeongniOut = path.join(runDir, "myeongni.json");
  const rationaleOut = path.join(runDir, "rationale.json");
  const mdOut = req.renderMd !== false ? path.join(runDir, "patient_facing.md") : undefined;

  fs.writeFileSync(intakePath, `${JSON.stringify(built.doc, null, 2)}\n`, "utf-8");

  const py = process.env.MKM_PYTHON?.trim() || "py";
  const args = [
    script,
    "--intake-json",
    intakePath,
    "--myeongni-out",
    myeongniOut,
    "--bundle-out",
    bundleOut,
    "--rationale-out",
    rationaleOut,
  ];

  if (req.briefOutput) args.push("--brief-output");
  if (req.validateSchema !== false) args.push("--validate-schema");
  if (req.validatePolicy !== false) args.push("--validate-policy");
  if (mdOut) args.push("--render-md-out", mdOut);

  const child = spawnSync(py, args, {
    cwd: root,
    encoding: "utf-8",
    maxBuffer: 12 * 1024 * 1024,
    timeout: 180_000,
    windowsHide: true,
  });

  if (child.status !== 0) {
    return {
      ok: false,
      error: (child.stderr || child.stdout || `exit ${child.status}`).trim().slice(0, 4000),
      stderr: child.stderr,
    };
  }

  if (!fs.existsSync(bundleOut)) {
    return { ok: false, error: `bundle output missing: ${bundleOut}`, stderr: child.stderr };
  }

  try {
    const bundle = JSON.parse(fs.readFileSync(bundleOut, "utf-8")) as Record<string, unknown>;
    const soap =
      bundle.clinical_soap_v1 && typeof bundle.clinical_soap_v1 === "object"
        ? (bundle.clinical_soap_v1 as Record<string, { text?: string }>)
        : {};
    const patientFacingMarkdown =
      mdOut && fs.existsSync(mdOut) ? fs.readFileSync(mdOut, "utf-8") : undefined;

    return {
      ok: true,
      slug: resolved.slug,
      refToken: String(resolved.pointer.ref_token || resolved.slug),
      displayLabel: String(resolved.pointer.display_label || resolved.slug),
      bundlePath: bundleOut,
      myeongniPath: myeongniOut,
      rationalePath: rationaleOut,
      markdownPath: mdOut,
      bundle,
      patientFacingMarkdown,
      soap,
    };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return { ok: false, error: `failed to read bundle: ${msg}` };
  }
}

export function listResolvableSlugs(root: string): string[] {
  const reports = path.join(root, "reports");
  if (!fs.existsSync(reports)) return [];
  return fs
    .readdirSync(reports)
    .map((name) => /^(.+)_intake_ssot_pointer_v1\.json$/.exec(name)?.[1])
    .filter((s): s is string => Boolean(s))
    .sort();
}

export function loadPointerForSlug(root: string, slug: string): PatientSsotPointer | null {
  return loadPatientPointer(root, slug);
}
