import fs from "node:fs";

import {
  buildConsultFromSimpleCopilot,
  buildPatientEducationCopy,
  computeMedicalCalcFromSimpleCopilot,
  mapResolvedToSimpleCopilotCards,
  type SimpleCopilotCardsV1,
  type SimpleCopilotMedicalCalcV1,
  type SimpleCopilotRequestV1,
  type SimpleCopilotSajuCalcV1,
} from "@/lib/clinician-simple-copilot-v1";
import { extractSajuLabelFromVerifyLite } from "@/lib/clinic-intake-birth-v1";
import { runIntegratedWellnessPublishChain } from "@/lib/integrated-wellness-python-bridge-v1";
import { runVerifyLiteEngine } from "@/lib/manseryeok-verify-lite-engine";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export type SimpleCopilotAdviceResultV1 =
  | {
      ok: true;
      cards: SimpleCopilotCardsV1;
      medicalCalc: SimpleCopilotMedicalCalcV1;
      sajuCalc: SimpleCopilotSajuCalcV1;
      patientEducationCopy: string;
      sasangInternal?: string;
    }
  | { ok: false; error: string; stderr?: string };

async function resolveSajuCalc(
  birthInstantUtc: string,
  ianaTz: string,
  birthTimeKnown: boolean,
  birthTimeDefaulted: boolean,
): Promise<SimpleCopilotSajuCalcV1> {
  try {
    const lite = await runVerifyLiteEngine({
      birth_instant_utc: birthInstantUtc,
      tz: ianaTz,
    });
    const label = extractSajuLabelFromVerifyLite(lite.myeongni_lite);
    return {
      birth_instant_utc: birthInstantUtc,
      iana_tz: ianaTz,
      birth_time_known: birthTimeKnown,
      birth_time_defaulted: birthTimeDefaulted,
      saju_label: label || null,
      saju_source: label ? "live" : "pending",
    };
  } catch {
    return {
      birth_instant_utc: birthInstantUtc,
      iana_tz: ianaTz,
      birth_time_known: birthTimeKnown,
      birth_time_defaulted: birthTimeDefaulted,
      saju_label: null,
      saju_source: "pending",
    };
  }
}

export async function runSimpleCopilotAdviceChain(
  body: SimpleCopilotRequestV1,
  workspaceRoot?: string,
): Promise<SimpleCopilotAdviceResultV1> {
  const root = workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_not_found" };

  const built = buildConsultFromSimpleCopilot(body);
  if (!built.ok) return { ok: false, error: built.error };

  const medicalCalc = computeMedicalCalcFromSimpleCopilot(body);
  const laneA = built.consult.lane_a_profile;
  const birthTimeKnown = Boolean(body.birth_time?.trim());
  const sajuCalc = await resolveSajuCalc(
    laneA.birth_instant_utc || "",
    laneA.iana_tz || "Asia/Seoul",
    birthTimeKnown,
    !birthTimeKnown,
  );

  const chain = runIntegratedWellnessPublishChain(
    {
      requestId: body.request_id,
      consult: built.consult,
      sasangCandidate: built.sasang,
      publishToNo1kmediPublic: false,
      publishToPersonadiaryPublic: false,
      publishToMkmlifePublic: false,
    },
    root,
  );

  if (!chain.ok) {
    return { ok: false, error: chain.error, stderr: chain.stderr };
  }

  let resolved: Record<string, unknown> = {};
  if (fs.existsSync(chain.resolvedPath)) {
    resolved = JSON.parse(fs.readFileSync(chain.resolvedPath, "utf-8")) as Record<string, unknown>;
  }

  const draftDisclaimer =
    typeof chain.no1kmediDraft?.disclaimer === "string" ? chain.no1kmediDraft.disclaimer : undefined;
  const cards = mapResolvedToSimpleCopilotCards(resolved, draftDisclaimer);
  const patientEducationCopy = buildPatientEducationCopy({
    chief_complaint: body.chief_complaint,
    cards,
    medical: medicalCalc,
    saju: sajuCalc,
  });

  const profile = (resolved.client_profile || {}) as Record<string, unknown>;
  const sasangInternal =
    typeof profile.sasang_internal === "string" && profile.sasang_internal !== "unknown"
      ? profile.sasang_internal
      : built.sasang !== "unknown"
        ? built.sasang
        : undefined;

  return { ok: true, cards, medicalCalc, sajuCalc, patientEducationCopy, sasangInternal };
}
