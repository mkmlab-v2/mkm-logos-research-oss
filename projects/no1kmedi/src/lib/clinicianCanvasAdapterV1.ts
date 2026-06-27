import type { MkmThinkingStep } from "@/components/trust-canvas/MkmPathThinkingTimeline";
import type { MkmTrustCanvasScopeBanner } from "@/components/trust-canvas/MkmTrustCanvasShell";

export type ClinicianCdsReasoningSlice = {
  syndrome_hypothesis?: string;
  care_direction?: string;
  caution?: string;
};

export function buildThinkingStepsFromCdsReasoning(
  reasoning?: ClinicianCdsReasoningSlice | null,
): MkmThinkingStep[] {
  if (!reasoning) return [];
  const steps: MkmThinkingStep[] = [];
  if (reasoning.syndrome_hypothesis?.trim()) {
    steps.push({ id: "syndrome", label: trimLabel(reasoning.syndrome_hypothesis, 48) });
  }
  if (reasoning.care_direction?.trim()) {
    steps.push({ id: "care", label: trimLabel(reasoning.care_direction, 48) });
  }
  if (reasoning.caution?.trim()) {
    steps.push({ id: "caution", label: trimLabel(reasoning.caution, 48) });
  }
  return steps;
}

function trimLabel(text: string, max: number): string {
  const t = text.replace(/\s+/g, " ").trim();
  return t.length <= max ? t : `${t.slice(0, max - 1)}…`;
}

export function buildClinicianCanvasScope(validationOk?: boolean): MkmTrustCanvasScopeBanner {
  return {
    label: "Clinician Canvas · CDSS assist stub",
    detail: "SOAP·graph assist · physician sign-off required",
    tags: [
      "pilot_assist",
      validationOk ? "km_cds_validation_ok" : "km_cds_pending",
      "send_gate HOLD",
    ],
  };
}
