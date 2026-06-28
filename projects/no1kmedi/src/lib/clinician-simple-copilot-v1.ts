/**
 * no1kmedi 심플 코파일럿 — 입력·4카드 매핑 (한의임상 Pack v0).
 */

import type { PatientConsultInputV1, SasangType } from "@/lib/cdss-contract";
import { resolveClinicBirthInstant } from "@/lib/clinic-intake-birth-v1";

export const HAN_MEDICINE_LORA_PACK_V0 = {
  schema: "no1kmedi_han_medicine_lora_pack_v0",
  version: "0.1.0",
  product_name_ko: "한의임상 Pack v0",
} as const;

export type SimpleCopilotRequestV1 = {
  schema?: "simple_copilot_request_v1";
  request_id: string;
  chief_complaint: string;
  birthdate: string;
  birth_time?: string;
  birth_time_known?: boolean;
  sasang_candidate?: string;
  onset?: string;
  severity?: string;
  pain_scale_0_10?: number;
  red_flags?: {
    chest_pain?: boolean;
    neuro_deficit?: boolean;
    dyspnea?: boolean;
    bleeding_or_high_fever?: boolean;
  };
};

export type CopilotCardItemV1 = {
  title: string;
  body: string;
  tier?: string;
  node_id?: string;
};

export type IwsSuppressionLogEntryV1 = {
  node_id: string;
  reason: string;
  tier?: string;
  triggered_by?: string;
};

export type SimpleCopilotCardsV1 = {
  schema: "simple_copilot_cards_v1";
  pack: typeof HAN_MEDICINE_LORA_PACK_V0;
  tcm_primary: { title: string; items: CopilotCardItemV1[] };
  modern_explain: { title: string; items: CopilotCardItemV1[]; non_gating: true };
  saju_aux: { title: string; items: CopilotCardItemV1[]; non_gating: true };
  physician_checklist: { title: string; items: string[] };
  /** IWS resolver suppressions — not mixed into physician_checklist (collapsible UI). */
  iws_suppression_log?: IwsSuppressionLogEntryV1[];
  disclaimer: string;
  human_confirm_required: boolean;
};

const SASANG_INTERNAL_TO_KO: Record<string, string> = {
  taeyang: "태양인",
  soyang: "소양인",
  soyag: "소양인",
  taeum: "태음인",
  taeeum: "태음인",
  soeum: "소음인",
};

export function formatSasangInternalLabel(code: string): string | null {
  const key = code.trim().toLowerCase();
  if (!key || key === "unknown") return null;
  return SASANG_INTERNAL_TO_KO[key] || null;
}

export function patchSoapAssessmentSasangFromIws(
  soap: Record<string, { text?: string }>,
  sasangInternal: string,
  source = "iws_resolver_v2",
): Record<string, { text?: string }> {
  const label = formatSasangInternalLabel(sasangInternal);
  if (!label) return soap;
  const assessment = soap.assessment?.text;
  if (!assessment || !assessment.includes("미입력")) return soap;

  const patchedText = assessment.replace(
    /\*\*미입력\*\*\s*\(출처 메모:\s*[^)]+\)/,
    `**${label}** (출처 메모: ${source})`,
  );
  if (patchedText === assessment) return soap;

  return {
    ...soap,
    assessment: { ...soap.assessment, text: patchedText },
  };
}

export type SimpleCopilotMedicalCalcV1 = {
  pain_scale_0_10: number;
  red_flag_count: number;
  triage_level: "routine" | "priority" | "emergency";
  triage_label_ko: string;
  recommended_action: string;
  acute_onset_suspected: boolean;
  rationale: string[];
};

export type CopilotCopyContextV1 = {
  chief_complaint: string;
  cards: SimpleCopilotCardsV1;
  medical?: SimpleCopilotMedicalCalcV1 | null;
  saju?: SimpleCopilotSajuCalcV1 | null;
};

const TRIAGE_LABEL_KO: Record<SimpleCopilotMedicalCalcV1["triage_level"], string> = {
  routine: "일반 관찰",
  priority: "우선 평가",
  emergency: "즉시 대면/응급 평가",
};

function detectAcuteOnset(onset?: string, complaint?: string): boolean {
  const text = `${onset || ""} ${complaint || ""}`.toLowerCase();
  if (!text.trim()) return false;
  return /(\d+\s*(일|주|시간|hour|day|week))|급성|갑자기|오늘|어제|acute|sudden/.test(text);
}

function isCriticalRedFlag(flags: NonNullable<SimpleCopilotRequestV1["red_flags"]>): boolean {
  return Boolean(flags.chest_pain || flags.neuro_deficit || flags.dyspnea);
}

export type SimpleCopilotSajuCalcV1 = {
  birth_instant_utc: string;
  iana_tz: string;
  birth_time_known: boolean;
  birth_time_defaulted: boolean;
  saju_label: string | null;
  saju_source: "live" | "pending";
};

type EvidenceNode = {
  node_id?: string;
  tier?: string;
  content_payload?: { title?: string; body?: string };
};

const SASANG_NORMALIZE: Record<string, SasangType> = {
  taeyang: "taeyang",
  soyag: "soyag",
  soyang: "soyag",
  taeeum: "taeeum",
  taeum: "taeeum",
  soeum: "soeum",
  unknown: "unknown",
};

export function buildConsultFromSimpleCopilot(
  body: SimpleCopilotRequestV1,
): { ok: true; consult: PatientConsultInputV1; sasang: string } | { ok: false; error: string } {
  if (!body.request_id?.trim()) return { ok: false, error: "missing_request_id" };
  const complaint = body.chief_complaint?.trim();
  if (!complaint) return { ok: false, error: "missing_chief_complaint" };

  const birth = resolveClinicBirthInstant({
    birthdate: body.birthdate,
    birthTime: body.birth_time,
    birthTimeKnown: body.birth_time_known,
  });
  if (!birth) return { ok: false, error: "invalid_birthdate" };

  const rawSasang = (body.sasang_candidate || "unknown").toLowerCase();
  const sasang = SASANG_NORMALIZE[rawSasang] || "unknown";

  const consult: PatientConsultInputV1 = {
    schema: "patient_consult_input_v1",
    request_id: body.request_id.trim(),
    actor_id: "no1kmedi_simple_copilot_v0",
    lane_a_profile: {
      birth_instant_utc: birth.birth_instant_utc,
      iana_tz: birth.iana_tz,
      constitution_survey: {},
    },
    lane_b_clinical: {
      chief_complaint: complaint,
      onset: (body.onset || "unknown").trim(),
      severity: (body.severity || "moderate").trim(),
      medication: "none_reported",
      health_survey: {},
    },
  };

  return { ok: true, consult, sasang };
}

export function computeMedicalCalcFromSimpleCopilot(body: SimpleCopilotRequestV1): SimpleCopilotMedicalCalcV1 {
  const painRaw = body.pain_scale_0_10;
  const pain_scale_0_10 =
    typeof painRaw === "number" && Number.isFinite(painRaw) ? Math.max(0, Math.min(10, Math.round(painRaw))) : 5;
  const redFlags = body.red_flags || {};
  const redFlagCount = Object.values(redFlags).filter(Boolean).length;
  const acute_onset_suspected = detectAcuteOnset(body.onset, body.chief_complaint);
  const rationale: string[] = [];

  if (redFlags.chest_pain) rationale.push("흉통 신호");
  if (redFlags.neuro_deficit) rationale.push("신경학적 결손 의심");
  if (redFlags.dyspnea) rationale.push("호흡곤란");
  if (redFlags.bleeding_or_high_fever) rationale.push("고열/출혈");

  let triageLevel: SimpleCopilotMedicalCalcV1["triage_level"] = "routine";

  if (isCriticalRedFlag(redFlags) || redFlagCount >= 2) {
    triageLevel = "emergency";
    rationale.push("중증 레드플래그 또는 복합 신호");
  } else if (redFlags.bleeding_or_high_fever) {
    triageLevel = "priority";
    rationale.push("고열/출혈 단독 — 우선 평가");
  } else if (pain_scale_0_10 >= 8) {
    triageLevel = "priority";
    rationale.push("통증 NRS 8 이상");
  } else if (pain_scale_0_10 >= 6 && acute_onset_suspected) {
    triageLevel = "priority";
    rationale.push("급성 경과 + 통증 NRS 6 이상");
  } else if (pain_scale_0_10 >= 7) {
    triageLevel = "priority";
    rationale.push("통증 NRS 7 이상");
  } else {
    rationale.push("레드플래그 없음 · 통증 중등도 이하");
  }

  const recommended_action =
    triageLevel === "emergency"
      ? "즉시 대면 진료 또는 응급실 연계를 검토하세요. 자동 처방/확정 금지."
      : triageLevel === "priority"
        ? "당일~48시간 내 재평가·추가 문진을 권장합니다."
        : "외래 관찰·생활관리 중심으로 진행하고 악화 시 재내원 안내.";

  return {
    pain_scale_0_10,
    red_flag_count: redFlagCount,
    triage_level: triageLevel,
    triage_label_ko: TRIAGE_LABEL_KO[triageLevel],
    recommended_action,
    acute_onset_suspected,
    rationale,
  };
}

function bulletLines(items: CopilotCardItemV1[]): string[] {
  return items.map((item) => `- ${item.title}: ${item.body}`);
}

export function buildChartSummaryCopy(ctx: CopilotCopyContextV1): string {
  const { cards, medical, saju, chief_complaint } = ctx;
  const sLines = [`주호소: ${chief_complaint.trim()}`];
  if (medical) {
    sLines.push(`통증 NRS: ${medical.pain_scale_0_10}/10`);
    sLines.push(`분류: ${medical.triage_label_ko} (${medical.triage_level})`);
    if (medical.acute_onset_suspected) sLines.push("경과: 급성 의심");
  }
  const oLines: string[] = [];
  if (saju?.saju_label) oLines.push(`사주 참고(보조): ${saju.saju_label}`);
  if (medical?.rationale.length) oLines.push(`리스크 근거: ${medical.rationale.join(", ")}`);

  return [
    "[진료 보조 차트 초안 — CDSS]",
    "",
    "[S]",
    ...sLines.map((l) => `  ${l}`),
    "",
    "[O]",
    ...(oLines.length ? oLines.map((l) => `  ${l}`) : ["  (추가 관찰 입력)"]),
    "",
    "[A]",
    ...bulletLines(cards.tcm_primary.items).map((l) => `  ${l}`),
    "",
    "[P]",
    ...bulletLines(cards.tcm_primary.items.filter((i) => i.tier === "ACTION" || i.tier === "POLICY")).map(
      (l) => `  ${l}`,
    ),
    ...(cards.physician_checklist.items.length
      ? ["", "  [확인]", ...cards.physician_checklist.items.map((l) => `  - ${l}`)]
      : []),
    "",
    `※ ${cards.disclaimer}`,
  ].join("\n");
}

export function buildPatientEducationCopy(ctx: CopilotCopyContextV1): string {
  const { cards, medical, chief_complaint } = ctx;
  const lifestyle = cards.tcm_primary.items.filter((i) => i.tier === "ACTION" || i.tier === "POLICY");
  const explain = cards.modern_explain.items;

  const warn =
    medical?.triage_level === "emergency"
      ? "증상이 빠르게 악화되거나 호흡곤란·가슴통증·의식저하가 있으면 즉시 병원을 방문해 주세요."
      : "증상이 갑자기 심해지면 지체하지 말고 진료를 받아 주세요.";

  return [
    "[환자 안내문 초안]",
    "",
    "오늘 말씀해 주신 증상을 바탕으로 생활관리 방향을 정리했습니다.",
    `주요 증상: ${chief_complaint.trim()}`,
    "",
    explain.length
      ? ["이해하기 쉬운 설명:", ...explain.slice(0, 3).map((i) => `- ${i.title}: ${i.body}`), ""].join("\n")
      : "",
    lifestyle.length
      ? ["생활관리 권장:", ...lifestyle.slice(0, 4).map((i) => `- ${i.title}: ${i.body}`), ""].join("\n")
      : "생활관리: 규칙적인 식사·수면·가벼운 활동을 유지해 주세요.\n",
    `주의: ${warn}`,
    "",
    "본 안내문은 참고용이며, 최종 진료·처방은 한의사가 확정합니다.",
  ]
    .filter(Boolean)
    .join("\n");
}

export function buildFullCopilotCopy(ctx: CopilotCopyContextV1): string {
  const { cards } = ctx;
  const section = (title: string, lines: string[]) =>
    [`## ${title}`, ...lines.map((line) => `- ${line}`), ""].join("\n");
  const mapItems = (items: CopilotCardItemV1[]) => items.map((item) => `${item.title}: ${item.body}`);

  return [
    `[${HAN_MEDICINE_LORA_PACK_V0.product_name_ko} v${HAN_MEDICINE_LORA_PACK_V0.version}]`,
    "",
    section(cards.tcm_primary.title, mapItems(cards.tcm_primary.items)),
    section(cards.modern_explain.title, mapItems(cards.modern_explain.items)),
    section(cards.saju_aux.title, mapItems(cards.saju_aux.items)),
    section(cards.physician_checklist.title, cards.physician_checklist.items),
    `※ ${cards.disclaimer}`,
  ].join("\n");
}

function nodeToItem(node: EvidenceNode): CopilotCardItemV1 | null {
  const title = node.content_payload?.title?.trim();
  const body = node.content_payload?.body?.trim();
  if (!title || !body) return null;
  return {
    title,
    body,
    tier: node.tier,
    node_id: node.node_id,
  };
}

export function mapResolvedToSimpleCopilotCards(
  resolved: Record<string, unknown>,
  draftDisclaimer?: string,
): SimpleCopilotCardsV1 {
  const stream = (resolved.resolved_evidence_stream || []) as EvidenceNode[];
  const suppressed = (resolved.suppression_log || []) as Array<{ node_id?: string; reason?: string }>;
  const boundary = (resolved.boundary_contract || {}) as Record<string, unknown>;
  const profile = (resolved.client_profile || {}) as Record<string, unknown>;
  const chief = (resolved.chief_concern || {}) as { title_ko?: string };

  const tcmItems: CopilotCardItemV1[] = [];
  const modernItems: CopilotCardItemV1[] = [];
  const sajuItems: CopilotCardItemV1[] = [];

  for (const node of stream) {
    const tier = (node.tier || "").toUpperCase();
    const id = (node.node_id || "").toLowerCase();
    const item = nodeToItem(node);
    if (!item) continue;

    if (tier === "FACT") {
      modernItems.push(item);
    } else if (tier === "NON_GATING" || id.includes("myeongni") || id.includes("logos") || id.includes("saju")) {
      sajuItems.push(item);
    } else if (tier === "HYPO" || tier === "ACTION" || tier === "POLICY") {
      tcmItems.push(item);
    }
  }

  if (chief.title_ko) {
    tcmItems.unshift({
      title: "주증상",
      body: chief.title_ko,
      tier: "CONTEXT",
    });
  }

  const sasang = profile.sasang_internal;
  if (typeof sasang === "string" && sasang !== "unknown") {
    const sasangDisplay = formatSasangInternalLabel(sasang) || sasang;
    tcmItems.unshift({
      title: "사상 체질 후보",
      body: `${sasangDisplay} (입력·resolver 기준, 확정 아님)`,
      tier: "CONTEXT",
    });
  }

  const checklist: string[] = [
    "최종 진단·처방·차트 기록은 한의사가 직접 확정합니다.",
    "CDSS 출력은 보조 초안이며 자동 처방이 아닙니다.",
  ];

  if (boundary.physician_final_authority_no1kmedi) {
    checklist.push("원장 최종 권한(physician_final_authority) 적용됨.");
  }

  const iwsSuppressionLog: IwsSuppressionLogEntryV1[] = [];
  for (const entry of suppressed) {
    if (entry.node_id && entry.reason) {
      iwsSuppressionLog.push({
        node_id: entry.node_id,
        reason: entry.reason,
        tier: typeof (entry as { tier?: string }).tier === "string" ? (entry as { tier?: string }).tier : undefined,
        triggered_by:
          typeof (entry as { triggered_by?: string }).triggered_by === "string"
            ? (entry as { triggered_by?: string }).triggered_by
            : undefined,
      });
    }
  }

  return {
    schema: "simple_copilot_cards_v1",
    pack: HAN_MEDICINE_LORA_PACK_V0,
    tcm_primary: { title: "한의학 평가·관리안", items: tcmItems },
    modern_explain: {
      title: "현대의학·근거 설명",
      items: modernItems,
      non_gating: true,
    },
    saju_aux: {
      title: "사주·시간축 보조",
      items: sajuItems,
      non_gating: true,
    },
    physician_checklist: {
      title: "원장 확인 체크리스트",
      items: checklist,
    },
    ...(iwsSuppressionLog.length ? { iws_suppression_log: iwsSuppressionLog } : {}),
    disclaimer:
      draftDisclaimer ||
      "본 출력은 연구·보조(B-track) 초안입니다. 최종 진료 판단은 한의사가 확정하며, 응급·중증 의심 시 대면 진료를 우선하세요.",
    human_confirm_required: true,
  };
}
