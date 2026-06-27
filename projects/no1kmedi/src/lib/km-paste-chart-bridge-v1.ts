import { resolveEncounterPatient } from "@/lib/clinician-encounter-artifacts-v1";
import { buildSimpleCopilotRequestFromPaste } from "@/lib/clinician-paste-chart-v1";
import type { SimpleCopilotCardsV1, SimpleCopilotMedicalCalcV1, SimpleCopilotSajuCalcV1 } from "@/lib/clinician-simple-copilot-v1";
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
      bundlePath: fusion.bundlePath,
      bundle: fusion.bundle,
      soap: fusion.soap,
      patientFacingMarkdown: fusion.patientFacingMarkdown,
      advice: null,
    };
  }

  const resolved = resolveEncounterPatient({
    root,
    slug: fusion.slug,
    refToken: fusion.refToken,
    display: fusion.displayLabel,
  });
  if ("error" in resolved) {
    return {
      ok: true,
      slug: fusion.slug,
      refToken: fusion.refToken,
      displayLabel: fusion.displayLabel,
      bundlePath: fusion.bundlePath,
      bundle: fusion.bundle,
      soap: fusion.soap,
      patientFacingMarkdown: fusion.patientFacingMarkdown,
      advice: null,
      advice_error: resolved.error,
    };
  }

  const birth = resolveEncounterBirthProfile(root, resolved.pointer, fusionReq);
  if (!birth) {
    return {
      ok: true,
      slug: fusion.slug,
      refToken: fusion.refToken,
      displayLabel: fusion.displayLabel,
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
    pointer: resolved.pointer,
    root,
    sasangOverride: req.sasangLabel,
  });
  if ("error" in copilotBody) {
    return {
      ok: true,
      slug: fusion.slug,
      refToken: fusion.refToken,
      displayLabel: fusion.displayLabel,
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
      bundlePath: fusion.bundlePath,
      bundle: fusion.bundle,
      soap: fusion.soap,
      patientFacingMarkdown: fusion.patientFacingMarkdown,
      advice: null,
      advice_error: advice.error,
      stderr: advice.stderr,
    };
  }

  return {
    ok: true,
    slug: fusion.slug,
    refToken: fusion.refToken,
    displayLabel: fusion.displayLabel,
    bundlePath: fusion.bundlePath,
    bundle: fusion.bundle,
    soap: fusion.soap,
    patientFacingMarkdown: fusion.patientFacingMarkdown,
    advice: {
      cards: advice.cards,
      medical_calc: advice.medicalCalc,
      saju_calc: advice.sajuCalc,
      patient_education_copy: advice.patientEducationCopy,
    },
  };
}
