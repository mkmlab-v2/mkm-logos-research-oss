/**
 * Eight-channel weight audit snapshot for ledger rows (Track B · audit only).
 * Does NOT prescribe or override human clinician decisions.
 */

import type { EncounterSessionEnvelopeV1 } from "@/lib/clinician-encounter-session-envelope-v1";
import {
  type EightChannelId,
  maxClinicalWeight,
} from "@/lib/clinician-ijeoma-eight-channel-contract-v1";

export type EightChannelAuditRowV1 = {
  channel_id: EightChannelId;
  weight_used: number;
  weight_max: number;
  within_cap: boolean;
  signal: string;
};

export type EightChannelAuditV1 = {
  schema: "clinician_paste_chart_eight_channel_audit_v1";
  decision_authority: "human_only";
  send_gate: "HOLD";
  channels: EightChannelAuditRowV1[];
};

function stageOk(envelope: EncounterSessionEnvelopeV1, id: string): boolean {
  return envelope.pipeline.some((s) => s.id === id && s.status === "ok");
}

function capRow(
  channelId: EightChannelId,
  weightUsed: number,
  signal: string,
): EightChannelAuditRowV1 {
  const weightMax = maxClinicalWeight(channelId);
  const weightUsedCapped = Math.min(weightUsed, weightMax);
  return {
    channel_id: channelId,
    weight_used: weightUsedCapped,
    weight_max: weightMax,
    within_cap: weightUsedCapped <= weightMax,
    signal,
  };
}

/** Build read-only audit rows from envelope + advice presence (no prescription logic). */
export function buildEightChannelAuditV1(
  envelope: EncounterSessionEnvelopeV1,
  opts?: { hasAdvice?: boolean },
): EightChannelAuditV1 {
  const hasAdvice = opts?.hasAdvice ?? envelope.output.hasAdvice;
  const extractConf = envelope.extract.confidence === "high" ? 0.85 : 0.55;
  const channels: EightChannelAuditRowV1[] = [
    capRow("ch01_chart_intake", stageOk(envelope, "chart_nonempty") ? 1 : 0, "chart_nonempty"),
    capRow(
      "ch02_extract_chips",
      stageOk(envelope, "extract_draft_ok") ? extractConf : 0,
      `extract_confidence_${envelope.extract.confidence}`,
    ),
    capRow("ch03_geumhwagyoyeok", 0, "not_wired_runtime"),
    capRow("ch04_bomyung_jiju", 0, "not_wired_runtime"),
    capRow("ch05_byeongjeung_yakri", hasAdvice && stageOk(envelope, "advice_gate_passed") ? 0.35 : 0, "advice_cards"),
    capRow(
      "ch06_sasang_core",
      /소음|태양|태음|소양/.test(envelope.input.chartText) ? 0.55 : 0,
      /소음|태양|태음|소양/.test(envelope.input.chartText) ? "chart_sasang_hint" : "absent",
    ),
    capRow("ch07_taeyang_sparsity", 0, "not_wired_runtime"),
    capRow("ch08_logos_non_gating", 0.05, "non_gating_placeholder"),
  ];
  return {
    schema: "clinician_paste_chart_eight_channel_audit_v1",
    decision_authority: "human_only",
    send_gate: "HOLD",
    channels,
  };
}
