/**
 * PersonaDiary voice → 4-lane classifier v1 [HYPO].
 * Mirrors scripts/classify_personadiary_voice_lane_hypo_v1.py (rule-only, no LLM).
 */

import type { PersonadiaryLane } from "./personadiaryMobileOpsV1";

export const VOICE_LANE_SOURCE = "voice_hypo_v1" as const;
export const VOICE_CLASSIFICATION_SCHEMA = "personadiary_voice_lane_classification_hypo_v1" as const;

export type MindRedFlagTier = "none" | "watch" | "shield_hypo" | "blocked";

export type VoiceLaneSegment = {
  lane: PersonadiaryLane;
  text: string;
  confidence: number;
  source: typeof VOICE_LANE_SOURCE;
  needs_review: boolean;
  blocked: boolean;
  matched_keywords?: string[];
  violation_codes?: string[];
};

export type VoiceLaneClassification = {
  schema: typeof VOICE_CLASSIFICATION_SCHEMA;
  version: 1;
  hypothesis_tier: "B";
  preview_only: true;
  send_gate_default: "HOLD";
  stt_event_id?: string;
  active_lane_hint?: PersonadiaryLane;
  segments: VoiceLaneSegment[];
  mind_red_flag_tier: MindRedFlagTier;
  human_gate_required: boolean;
  forbidden_blocked_count: number;
};

const LANES: PersonadiaryLane[] = ["body", "mind", "work", "rest"];

const LANE_KEYWORDS: Record<PersonadiaryLane, readonly string[]> = {
  body: ["수면", "잠", "몸", "통증", "아프", "식사", "밥", "운동", "컨디션", "피곤", "두통", "소화", "몸무게", "건강"],
  mind: ["기분", "마음", "불안", "우울", "스트레스", "걱정", "짜증", "외로", "스크롤", "숏폼", "집중", "산만", "자책", "비교", "관계", "감정"],
  work: ["업무", "일", "마감", "회의", "프로젝트", "할일", "출근", "보고", "미팅", "과제", "직장", "업체"],
  rest: ["휴식", "쉼", "쉬", "여가", "명상", "산책", "독서", "음악", "취미", "휴가", "낮잠"],
};

const PRIORITY: PersonadiaryLane[] = ["work", "body", "mind", "rest"];

const CLINICAL_FORBIDDEN = ["soap", "주관적", "객관적", "평가", "계획", "체질", "소음인", "소양인", "태음인", "태양인", "탕", "처방", "진단"];

const FORBIDDEN_SUBSTRINGS = ["적중률", "적중", "운세", "forecast", "prophecy", "hit rate", "Brier", "일운"];

const NEGATION_EXEMPT = ["아님", "아닙니다", "없음", "금지", "단정 없", "하지 않", "not a", "no forecast"];

const WATCH_KEYWORDS = ["새벽", "두 시", "2시", "02:", "숏폼", "스크롤", "네 시간", "4시간", "못 잤", "잠 못", "밤새"];

const SHIELD_KEYWORDS = ["자해", "죽고 싶", "살고 싶지", "극단적", "약물 남용", "약을 많이"];

function normalize(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function splitSegments(text: string): string[] {
  const raw = text.replace(/\r\n/g, "\n").trim();
  if (!raw) return [];
  const parts = raw.split(/(?<=[.!?…])\s+|\n+/);
  return parts.map((p) => p.trim()).filter(Boolean);
}

function hasNegationExempt(text: string): boolean {
  const lowered = text.toLowerCase();
  return NEGATION_EXEMPT.some((ex) => lowered.includes(ex.toLowerCase()));
}

function findForbiddenViolations(text: string): string[] {
  const s = String(text || "");
  if (!s.trim() || hasNegationExempt(s)) return [];
  const violations: string[] = [];
  for (const token of FORBIDDEN_SUBSTRINGS) {
    if (s.toLowerCase().includes(token.toLowerCase())) violations.push(`forbidden_substring:${token}`);
  }
  if (/\d\s*%|\d+%/.test(s) && !hasNegationExempt(s)) violations.push("forbidden_regex:percent");
  if (s.includes("예언") && !hasNegationExempt(s)) violations.push("forbidden_substring:예언");
  return violations;
}

function clinicalForbiddenHits(text: string): string[] {
  const norm = normalize(text).toLowerCase();
  return CLINICAL_FORBIDDEN.filter((t) => norm.includes(t.toLowerCase())).map((t) => `clinical_forbidden:${t}`);
}

function pickLane(
  scores: Record<PersonadiaryLane, number>,
  matched: Record<PersonadiaryLane, string[]>,
  activeLaneHint?: PersonadiaryLane
): { lane: PersonadiaryLane; confidence: number; matched_keywords: string[] } {
  const best = Math.max(...LANES.map((l) => scores[l]));
  if (best === 0) {
    const hint = activeLaneHint && LANES.includes(activeLaneHint) ? activeLaneHint : "mind";
    return { lane: hint, confidence: 0.45, matched_keywords: [] };
  }
  const winners = PRIORITY.filter((lane) => scores[lane] === best);
  const lane =
    activeLaneHint && winners.includes(activeLaneHint) ? activeLaneHint : winners[0] ?? "mind";
  const confidence = Math.min(0.95, 0.5 + 0.1 * best);
  return { lane, confidence: Math.round(confidence * 100) / 100, matched_keywords: matched[lane]?.slice(0, 5) ?? [] };
}

function laneScores(segment: string): {
  scores: Record<PersonadiaryLane, number>;
  matched: Record<PersonadiaryLane, string[]>;
} {
  const norm = normalize(segment).toLowerCase();
  const scores = { body: 0, mind: 0, work: 0, rest: 0 };
  const matched: Record<PersonadiaryLane, string[]> = { body: [], mind: [], work: [], rest: [] };
  for (const lane of LANES) {
    for (const kw of LANE_KEYWORDS[lane]) {
      if (norm.includes(kw)) {
        scores[lane] += 1;
        matched[lane].push(kw);
      }
    }
  }
  return { scores, matched };
}

function mindRedFlagTier(fullText: string, segments: VoiceLaneSegment[]): MindRedFlagTier {
  const norm = normalize(fullText).toLowerCase();
  if (SHIELD_KEYWORDS.some((kw) => norm.includes(kw))) return "shield_hypo";
  if (WATCH_KEYWORDS.some((kw) => norm.includes(kw))) return "watch";
  if (segments.some((s) => s.blocked)) return "blocked";
  return "none";
}

export function classifyVoiceTranscript(
  text: string,
  options?: { activeLaneHint?: PersonadiaryLane; sttEventId?: string }
): VoiceLaneClassification {
  let chunks = splitSegments(text);
  if (!chunks.length && text.trim()) chunks = [normalize(text)];

  const segments: VoiceLaneSegment[] = chunks.map((chunk) => {
    const violations = findForbiddenViolations(chunk);
    const clinical = clinicalForbiddenHits(chunk);
    const blocked = violations.length > 0 || clinical.length > 0;
    if (blocked) {
      return {
        lane: "mind",
        text: chunk,
        confidence: 0,
        source: VOICE_LANE_SOURCE,
        needs_review: true,
        blocked: true,
        violation_codes: [...violations, ...clinical],
      };
    }
    const { scores, matched } = laneScores(chunk);
    const picked = pickLane(scores, matched, options?.activeLaneHint);
    const needsReview = picked.confidence < 0.55;
    return {
      lane: needsReview ? "mind" : picked.lane,
      text: chunk,
      confidence: picked.confidence,
      source: VOICE_LANE_SOURCE,
      needs_review: needsReview,
      blocked: false,
      matched_keywords: picked.matched_keywords,
    };
  });

  const fullText = chunks.join("\n");
  const tier = mindRedFlagTier(fullText, segments);
  const humanGateRequired =
    tier === "shield_hypo" ||
    tier === "blocked" ||
    segments.some((s) => s.needs_review || s.blocked);

  return {
    schema: VOICE_CLASSIFICATION_SCHEMA,
    version: 1,
    hypothesis_tier: "B",
    preview_only: true,
    send_gate_default: "HOLD",
    stt_event_id: options?.sttEventId,
    active_lane_hint: options?.activeLaneHint,
    segments,
    mind_red_flag_tier: tier,
    human_gate_required: humanGateRequired,
    forbidden_blocked_count: segments.filter((s) => s.blocked).length,
  };
}

export function formatVoiceSegmentsForDiary(
  segments: VoiceLaneSegment[],
  laneLabels: Record<PersonadiaryLane, string>
): string {
  const approved = segments.filter((s) => !s.blocked);
  if (!approved.length) return "";
  return approved
    .map((s) => `[${laneLabels[s.lane]}] ${s.text}`)
    .join("\n")
    .slice(0, 2000);
}

export const VOICE_HUMAN_GATE_TEXT_KO =
  "음성 초안을 확인했습니다 · 예언·처방 아님 · 이 기기에만 저장";

export const VOICE_PHASE_2B_DISCLAIMER_KO =
  "말로 적기 · 붙여넣기 또는 브라우저 음성 인식 · Human Gate 후 저장 · 예언·처방 아님";

export const VOICE_PHASE_3_MIC_LABEL_KO = "마이크로 말하기";
export const VOICE_PHASE_3_LISTENING_KO = "듣는 중… (최대 45초 · 이 기기에서만 처리)";
export const VOICE_PHASE_3_UNSUPPORTED_KO =
  "이 브라우저는 내장 음성 인식을 지원하지 않습니다. 전사를 붙여넣어 주세요.";
