/**
 * Clinical 8-channel weight contract — read-only pointer (Track B · human_only).
 * SSOT: docs/final/artifacts/clinician_ijeoma_eight_channel_weight_contract_v1.json
 */

import contract from "../../../../docs/final/artifacts/clinician_ijeoma_eight_channel_weight_contract_v1.json";

export type EightChannelId =
  | "ch01_chart_intake"
  | "ch02_extract_chips"
  | "ch03_geumhwagyoyeok"
  | "ch04_bomyung_jiju"
  | "ch05_byeongjeung_yakri"
  | "ch06_sasang_core"
  | "ch07_taeyang_sparsity"
  | "ch08_logos_non_gating";

export type EightChannelRow = {
  channel_id: EightChannelId;
  label_ko: string;
  tier: number;
  clinical_weight_max: number;
  role_ko: string;
  non_gating?: boolean;
};

const CHANNELS = contract.channels as EightChannelRow[];

export function eightChannelContractForDebug(): typeof contract {
  return contract;
}

export function listEightChannels(): EightChannelRow[] {
  return [...CHANNELS];
}

export function getEightChannel(channelId: EightChannelId): EightChannelRow | undefined {
  return CHANNELS.find((c) => c.channel_id === channelId);
}

export function maxClinicalWeight(channelId: EightChannelId): number {
  return getEightChannel(channelId)?.clinical_weight_max ?? 0;
}

/** Ordered channel ids for UI pipeline / reference panels (no auto prescription). */
export function eightChannelSynthesisOrder(): EightChannelId[] {
  return (contract.synthesis_order as EightChannelId[]) || [];
}
