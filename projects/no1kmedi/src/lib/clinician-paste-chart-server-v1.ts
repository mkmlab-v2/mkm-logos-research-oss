/**
 * Server-only Paste Chart helpers (node:fs). Import from API routes only.
 */

import fs from "node:fs";
import path from "node:path";

import { buildChiefComplaintFromPaste } from "@/lib/clinician-intake-paste-v1";
import { extractChiefComplaintFromPaste } from "@/lib/clinician-chart-paste-extract-v1";
import { birthInstantToClinicBirthFields } from "@/lib/clinician-paste-chart-v1";
import { inferSasangCandidateFromLabel } from "@/lib/clinician-sasang-infer-v1";
import type { SimpleCopilotRequestV1 } from "@/lib/clinician-simple-copilot-v1";
import type { PatientSsotPointer } from "@/lib/clinician-patient-slug-v1";
import type { EncounterBirthProfileV1 } from "@/lib/km-intake-fusion-draft-bridge-v1";

function loadSasangHintFromPointer(root: string, pointer: PatientSsotPointer): string {
  const rel = pointer.paths?.patient_track_b_memory;
  if (!rel) return "unknown";
  const abs = path.join(root, rel);
  if (!fs.existsSync(abs)) return "unknown";
  try {
    const doc = JSON.parse(fs.readFileSync(abs, "utf-8")) as {
      clinical_summary?: { constitution_physician?: string };
    };
    const label = doc.clinical_summary?.constitution_physician;
    return label ? inferSasangCandidateFromLabel(label) : "unknown";
  } catch {
    return "unknown";
  }
}

function extractOnsetFromPaste(text: string): string | undefined {
  const m = text.match(/(\d+\s*(?:일|주|개월|시간|년))\s*(?:째|전|부터)?/);
  if (m?.[1]) return m[1].trim();
  if (/급성|갑자기|어제|오늘/.test(text)) return "급성";
  return undefined;
}

export function buildSimpleCopilotRequestFromPaste(args: {
  requestId: string;
  chartText: string;
  birth: EncounterBirthProfileV1;
  pointer: PatientSsotPointer;
  root: string;
  sasangOverride?: string;
  birthTimeKnown?: boolean;
}): SimpleCopilotRequestV1 | { error: string } {
  const chief = extractChiefComplaintFromPaste(args.chartText) || buildChiefComplaintFromPaste(args.chartText);
  if (!chief) return { error: "chart_text_required" };

  const birthFields = birthInstantToClinicBirthFields(
    args.birth.birth_instant_utc,
    args.birth.iana_tz,
    args.birthTimeKnown,
  );
  if (!birthFields) return { error: "invalid_birth_profile" };

  const sasangFromChart = inferSasangCandidateFromLabel(args.chartText);
  const sasang =
    args.sasangOverride?.trim() ||
    loadSasangHintFromPointer(args.root, args.pointer) ||
    (sasangFromChart !== "unknown" ? sasangFromChart : "unknown");

  return {
    schema: "simple_copilot_request_v1",
    request_id: args.requestId,
    chief_complaint: chief,
    onset: extractOnsetFromPaste(args.chartText) || "미기재",
    birthdate: birthFields.birthdate,
    birth_time: birthFields.birth_time,
    birth_time_known: birthFields.birth_time_known,
    sasang_candidate: sasang,
    pain_scale_0_10: 5,
    red_flags: {},
  };
}
