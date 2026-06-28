import { buildSimpleCopilotRequestFromPaste, inferSasangCandidateFromLabel } from "@/lib/clinician-paste-chart-v1";
import {
  patchSoapAssessmentSasangFromIws,
  type SimpleCopilotCardsV1,
  type SimpleCopilotMedicalCalcV1,
  type SimpleCopilotSajuCalcV1,
} from "@/lib/clinician-simple-copilot-v1";
import {
  resolveEncounterBirthProfile,
  runIntakeFusionDraftChain,
  type IntakeFusionDraftRequestV1,
} from "@/lib/km-intake-fusion-draft-bridge-v1";
import { runSimpleCopilotAdviceChain } from "@/lib/km-simple-copilot-chain-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export type PasteChartRequestV1 = IntakeFusionDraftRequestV1 & {
  chartText?: string;
  skipAdvice?: boolean;
};

export type PasteChartAdviceBlockV1 = {
  cards: SimpleCopilotCardsV1;
  medical_calc: SimpleCopilotMedicalCalcV1;
  saju_calc: SimpleCopilotSajuCalcV1;
  patient_education_copy: string;
};

export type PasteChartResultV1 =
  | {
      ok: true;
      slug: string;
      refToken: string;
      displayLabel: string;
      ephemeral?: boolean;
      bundlePath: string;
      bundle: Record<string, unknown>;
      soap: Record<string, { text?: string }>;
      patientFacingMarkdown?: string;
      advice: PasteChartAdviceBlockV1 | null;
      advice_error?: string;
      stderr?: string;
    }
  | { ok: false; error: string; stderr?: string; advice_error?: string };

export async function runPasteChartV1Chain(
  req: PasteChartRequestV1,
  workspaceRoot?: string,
): Promise<PasteChartResultV1> {
  const root = workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_not_found" };

  const chartText = String(req.chartText || req.intakeText || "").trim();
  if (!chartText) return { ok: false, error: "chart_text_required" };

  const fusionReq: IntakeFusionDraftRequestV1 = { ...req, intakeText: chartText };
  const fusion = runIntakeFusionDraftChain(fusionReq, root);
  if (!fusion.ok) return fusion;

  if (req.skipAdvice) {
    return {
      ok: true,
      slug: fusion.slug,
      refToken: fusion.refToken,
      displayLabel: fusion.displayLabel,
      ephemeral: fusion.ephemeral,
      bundlePath: fusion.bundlePath,
      bundle: fusion.bundle,
      soap: fusion.soap,
      patientFacingMarkdown: fusion.patientFacingMarkdown,
      advice: null,
    };
  }

  const pointer = fusion.pointer;
  const birth = resolveEncounterBirthProfile(root, pointer, fusionReq);
  if (!birth) {
    return {
      ok: true,
      slug: fusion.slug,
      refToken: fusion.refToken,
      displayLabel: fusion.displayLabel,
      ephemeral: fusion.ephemeral,
      bundlePath: fusion.bundlePath,
      bundle: fusion.bundle,
      soap: fusion.soap,
      patientFacingMarkdown: fusion.patientFacingMarkdown,
      advice: null,
      advice_error: "birth_profile_missing",
    };
  }

  const requestId = `paste_chart_${fusion.slug}_${Date.now()}`;
  const copilotBody = buildSimpleCopilotRequestFromPaste({
    requestId,
    chartText,
    birth,
    pointer,
    root,
    sasangOverride: req.sasangLabel,
  });
  if ("error" in copilotBody) {
    return {
      ok: true,
      slug: fusion.slug,
      refToken: fusion.refToken,
      displayLabel: fusion.displayLabel,
      ephemeral: fusion.ephemeral,
      bundlePath: fusion.bundlePath,
      bundle: fusion.bundle,
      soap: fusion.soap,
      patientFacingMarkdown: fusion.patientFacingMarkdown,
      advice: null,
      advice_error: copilotBody.error,
    };
  }

  const advice = await runSimpleCopilotAdviceChain(copilotBody, root);
  if (!advice.ok) {
    return {
      ok: true,
      slug: fusion.slug,
      refToken: fusion.refToken,
      displayLabel: fusion.displayLabel,
      ephemeral: fusion.ephemeral,
      bundlePath: fusion.bundlePath,
      bundle: fusion.bundle,
      soap: fusion.soap,
      patientFacingMarkdown: fusion.patientFacingMarkdown,
      advice: null,
      advice_error: advice.error,
      stderr: advice.stderr,
    };
  }

  let soap = fusion.soap;
  let bundle = fusion.bundle;
  const sasangForPatch =
    advice.sasangInternal ||
    (copilotBody.sasang_candidate && copilotBody.sasang_candidate !== "unknown"
      ? copilotBody.sasang_candidate
      : undefined) ||
    (() => {
      const inferred = inferSasangCandidateFromLabel(chartText);
      return inferred !== "unknown" ? inferred : undefined;
    })() ||
    (() => {
      for (const item of advice.cards.tcm_primary.items) {
        const hit = inferSasangCandidateFromLabel(`${item.title} ${item.body}`);
        if (hit !== "unknown") return hit;
      }
      return undefined;
    })();
  if (sasangForPatch) {
    soap = patchSoapAssessmentSasangFromIws(soap, sasangForPatch);
    if (bundle.clinical_soap_v1 && typeof bundle.clinical_soap_v1 === "object") {
      bundle = {
        ...bundle,
        clinical_soap_v1: patchSoapAssessmentSasangFromIws(
          bundle.clinical_soap_v1 as Record<string, { text?: string }>,
          sasangForPatch,
        ),
      };
    }
  }

  return {
    ok: true,
    slug: fusion.slug,
    refToken: fusion.refToken,
    displayLabel: fusion.displayLabel,
    ephemeral: fusion.ephemeral,
    bundlePath: fusion.bundlePath,
    bundle,
    soap,
    patientFacingMarkdown: fusion.patientFacingMarkdown,
    advice: {
      cards: advice.cards,
      medical_calc: advice.medicalCalc,
      saju_calc: advice.sajuCalc,
      patient_education_copy: advice.patientEducationCopy,
    },
  };
}
