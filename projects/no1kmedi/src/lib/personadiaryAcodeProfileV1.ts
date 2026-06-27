import type { DailyGuidePackage } from "./personadiaryDailyGuide";
import { sanitizeMomentLine } from "./personadiaryMomentDisplay";
import {
  PERSONADIARY_CLINIC_PACK,
  PERSONADIARY_CLINIC_SCALE_MAX,
} from "./personadiaryClinicConstitutionSurveyV1";

export const PERSONADIARY_ACODE_SCHEMA = "personadiary_acode_persona_v1" as const;

type AcodeAxis = "S" | "L" | "K" | "M";
type AcodePhase = 1 | 2 | 3;

type AcodeMeta = {
  axis_label_ko: string;
  title_ko: string;
  moment_tone_ko: string;
  meal_tone_ko: string;
};

const ACODE_META: Record<`${AcodeAxis}${AcodePhase}`, AcodeMeta> = {
  S1: {
    axis_label_ko: "스파크",
    title_ko: "시작 점화형",
    moment_tone_ko: "짧게 시작하고 바로 몸을 움직여요.",
    meal_tone_ko: "가볍게 힘 올리는 따뜻한 한 그릇",
  },
  S2: {
    axis_label_ko: "스파크",
    title_ko: "리듬 가속형",
    moment_tone_ko: "리듬은 올리고 과열은 피하는 날이에요.",
    meal_tone_ko: "담백 단백질 + 맑은 국물 조합",
  },
  S3: {
    axis_label_ko: "스파크",
    title_ko: "정리 착지형",
    moment_tone_ko: "마무리 체크리스트를 먼저 붙여요.",
    meal_tone_ko: "속 편한 국물 + 과하지 않은 탄수화물",
  },
  L1: {
    axis_label_ko: "라이프",
    title_ko: "감각 탐색형",
    moment_tone_ko: "오늘은 감각과 취향을 가볍게 실험해요.",
    meal_tone_ko: "산뜻한 채소 + 깔끔한 면/밥",
  },
  L2: {
    axis_label_ko: "라이프",
    title_ko: "실행 몰입형",
    moment_tone_ko: "한 가지를 고르고 깊게 몰입해요.",
    meal_tone_ko: "집중 유지용 담백·균형 메뉴",
  },
  L3: {
    axis_label_ko: "라이프",
    title_ko: "회복 정돈형",
    moment_tone_ko: "속도를 낮추고 숨 고르기를 우선해요.",
    meal_tone_ko: "부담 적은 죽·수프·부드러운 메뉴",
  },
  K1: {
    axis_label_ko: "키핑",
    title_ko: "기준 세팅형",
    moment_tone_ko: "오늘 기준 한 줄을 먼저 세워요.",
    meal_tone_ko: "기본기 있는 따뜻한 집밥 계열",
  },
  K2: {
    axis_label_ko: "키핑",
    title_ko: "균형 유지형",
    moment_tone_ko: "균형을 지키며 우선순위를 정리해요.",
    meal_tone_ko: "기름기 낮춘 균형 한 상",
  },
  K3: {
    axis_label_ko: "키핑",
    title_ko: "노이즈 정리형",
    moment_tone_ko: "잡음을 줄이고 핵심만 남겨요.",
    meal_tone_ko: "자극 적은 편안한 메뉴",
  },
  M1: {
    axis_label_ko: "마인드",
    title_ko: "관찰 오프닝형",
    moment_tone_ko: "몸·마음 신호를 가볍게 관찰해요.",
    meal_tone_ko: "천천히 먹기 좋은 따뜻한 메뉴",
  },
  M2: {
    axis_label_ko: "마인드",
    title_ko: "정서 페이싱형",
    moment_tone_ko: "감정 리듬을 맞추며 대화를 고릅니다.",
    meal_tone_ko: "속 편하고 안정감 주는 메뉴",
  },
  M3: {
    axis_label_ko: "마인드",
    title_ko: "휴식 회복형",
    moment_tone_ko: "쉼을 일정처럼 예약하는 날이에요.",
    meal_tone_ko: "부드럽고 소화 편한 회복 메뉴",
  },
};

function sectionLines(pkg: DailyGuidePackage, id: string): string[] {
  const sec = (pkg.sections || []).find((s) => s.id === id);
  return (sec?.lines || []).map((l) => sanitizeMomentLine(String(l))).filter(Boolean);
}

function axisScores(pkg: DailyGuidePackage): Record<AcodeAxis, number> {
  const world = sectionLines(pkg, "world_pulse").join(" ");
  const life = sectionLines(pkg, "lifestyle").join(" ");
  const myeongni = sectionLines(pkg, "myeongni").join(" ");
  const mkm = sectionLines(pkg, "mkm_4ai").join(" ");

  return {
    S: (world.match(/속보|헤드라인|변동|결정|타이밍|기회|리듬/g) || []).length,
    L: (life.match(/스타일|컬러|옷|메뉴|식사|날씨|산책|루틴/g) || []).length,
    K: (myeongni.match(/흐름|균형|정리|기준|집중|확장|수렴/g) || []).length,
    M: (mkm.match(/마음|페이싱|회복|호흡|코칭|관찰|대화/g) || []).length,
  };
}

function pickAxis(scores: Record<AcodeAxis, number>): AcodeAxis {
  const order: AcodeAxis[] = ["K", "M", "L", "S"];
  return order.reduce((best, axis) => (scores[axis] > scores[best] ? axis : best), "K");
}

function pickPhase(pkg: DailyGuidePackage, surveyResponses?: Record<string, number>): AcodePhase {
  const seed = [
    pkg.profile_id || "",
    pkg.calendar_kst || "",
    sectionLines(pkg, "world_pulse")[0] || "",
    sectionLines(pkg, "myeongni")[0] || "",
    surveyResponses ? JSON.stringify(surveyResponses) : "",
  ].join("|");
  const checksum = [...seed].reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  return ((checksum % 3) + 1) as AcodePhase;
}

const SURVEY_AXIS_TO_ACODE: Record<string, AcodeAxis> = {
  activity_lean: "S",
  digestion_lean: "L",
  cold_heat_lean: "L",
  moisture_lean: "K",
};

export function surveyBoostForAcodeAxis(
  surveyResponses?: Record<string, number>
): Partial<Record<AcodeAxis, number>> {
  if (!surveyResponses || !Object.keys(surveyResponses).length) return {};

  const axisTotals: Record<string, { sum: number; n: number }> = {};
  for (const item of PERSONADIARY_CLINIC_PACK.items) {
    const value = surveyResponses[item.item_id];
    if (typeof value !== "number" || value < 0 || value > PERSONADIARY_CLINIC_SCALE_MAX) {
      continue;
    }
    const bucket = axisTotals[item.axis] ?? { sum: 0, n: 0 };
    bucket.sum += value;
    bucket.n += 1;
    axisTotals[item.axis] = bucket;
  }

  const boost: Partial<Record<AcodeAxis, number>> = {};
  for (const [surveyAxis, acodeAxis] of Object.entries(SURVEY_AXIS_TO_ACODE)) {
    const totals = axisTotals[surveyAxis];
    if (!totals?.n) continue;
    const avg = totals.sum / totals.n / PERSONADIARY_CLINIC_SCALE_MAX;
    boost[acodeAxis] = (boost[acodeAxis] ?? 0) + avg * 2;
  }

  const fatigue = surveyResponses.ac02;
  if (typeof fatigue === "number" && fatigue >= 0) {
    boost.M = (boost.M ?? 0) + (fatigue / PERSONADIARY_CLINIC_SCALE_MAX) * 2;
  }

  return boost;
}

export type DerivePersonadiaryAcodeOptions = {
  surveyResponses?: Record<string, number>;
};

export type PersonadiaryAcodePersonaV1 = {
  schema: typeof PERSONADIARY_ACODE_SCHEMA;
  preview_only: true;
  public_code: `AC-${AcodeAxis}${AcodePhase}`;
  cell_code: `${AcodeAxis}${AcodePhase}`;
  axis_label_ko: string;
  title_ko: string;
  moment_tone_ko: string;
  meal_tone_ko: string;
};

export function derivePersonadiaryAcodeProfile(
  pkg: DailyGuidePackage,
  options?: DerivePersonadiaryAcodeOptions
): PersonadiaryAcodePersonaV1 {
  const scores = axisScores(pkg);
  const boost = surveyBoostForAcodeAxis(options?.surveyResponses);
  for (const axis of ["S", "L", "K", "M"] as AcodeAxis[]) {
    scores[axis] += Math.round(boost[axis] ?? 0);
  }
  const axis = pickAxis(scores);
  const phase = pickPhase(pkg, options?.surveyResponses);
  const cellCode = `${axis}${phase}` as const;
  const meta = ACODE_META[cellCode];
  return {
    schema: PERSONADIARY_ACODE_SCHEMA,
    preview_only: true,
    public_code: `AC-${cellCode}`,
    cell_code: cellCode,
    axis_label_ko: meta.axis_label_ko,
    title_ko: meta.title_ko,
    moment_tone_ko: meta.moment_tone_ko,
    meal_tone_ko: meta.meal_tone_ko,
  };
}
