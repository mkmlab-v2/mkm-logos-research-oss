/**
 * Shared constitution survey schema (patient presurvey).
 * Repo prebuild sync may refresh from mkm-life; keep in sync on questionnaire changes.
 */
export const CONSTITUTION_SURVEY_SCHEMA_VERSION = "constitution-survey-v1";

export type ConstitutionQuestionOption = "a" | "b";
export type ConstitutionQuestionId =
  | "q01"
  | "q02"
  | "q03"
  | "q04"
  | "q05"
  | "q06"
  | "q07"
  | "q08"
  | "q09"
  | "q10"
  | "q11"
  | "q12"
  | "q13"
  | "q14"
  | "q15";

export const CONSTITUTION_QUESTIONS: Array<{
  id: ConstitutionQuestionId;
  prompt: string;
  optionA: string;
  optionB: string;
}> = [
  { id: "q01", prompt: "압박 상황에서 먼저 보이는 반응은?", optionA: "즉시 말하거나 행동으로 푼다", optionB: "내부 정리 후 조용히 대응한다" },
  { id: "q02", prompt: "업무/생활 루틴 선호는?", optionA: "새 시도와 변화를 자주 준다", optionB: "안정적인 루틴을 유지한다" },
  { id: "q03", prompt: "식사 후 컨디션은 주로?", optionA: "든든하고 에너지가 유지된다", optionB: "더부룩하거나 쉽게 처진다" },
  { id: "q04", prompt: "의사결정 속도는?", optionA: "빠르게 결정하고 보완한다", optionB: "충분히 검토 후 결정한다" },
  { id: "q05", prompt: "갈등 상황에서의 기본 태도는?", optionA: "바로 조정·해결을 시도한다", optionB: "거리두며 관찰 후 대응한다" },
  { id: "q06", prompt: "추위/더위 민감도는?", optionA: "더위에 상대적으로 강하다", optionB: "추위를 더 민감하게 느낀다" },
  { id: "q07", prompt: "피로가 왔을 때 회복 방식은?", optionA: "휴식하면 비교적 빨리 회복", optionB: "회복에 시간이 오래 걸린다" },
  { id: "q08", prompt: "운동 후 몸 상태는?", optionA: "몸이 가볍고 개운하다", optionB: "쉽게 지치거나 무겁다" },
  { id: "q09", prompt: "대인관계 에너지 사용은?", optionA: "사람들과 상호작용할수록 에너지 상승", optionB: "혼자 정리 시간이 필요하다" },
  { id: "q10", prompt: "소화/식욕 패턴은?", optionA: "식욕이 비교적 안정적이다", optionB: "스트레스 시 식욕 변동이 크다" },
  { id: "q11", prompt: "수면 패턴은?", optionA: "짧아도 활동 유지가 가능하다", optionB: "수면이 부족하면 컨디션 저하가 크다" },
  { id: "q12", prompt: "업무 스타일은?", optionA: "멀티태스킹/병렬 처리가 편하다", optionB: "순차 처리/집중 처리가 편하다" },
  { id: "q13", prompt: "감정 표현 방식은?", optionA: "표현이 비교적 즉각적이다", optionB: "표현 전 내부 정리가 필요하다" },
  { id: "q14", prompt: "컨디션 저하 신호는?", optionA: "몸이 무겁고 둔해진다", optionB: "예민/긴장감이 올라간다" },
  { id: "q15", prompt: "장기 과제 수행 스타일은?", optionA: "시작 속도가 빠르고 추진력이 강하다", optionB: "지속성과 정밀도를 중시한다" },
];

export const CORE_CONSTITUTION_QUESTION_IDS: ConstitutionQuestionId[] = ["q01", "q02", "q03", "q04", "q05"];

export const DEFAULT_CONSTITUTION_ANSWERS: Record<ConstitutionQuestionId, ""> = {
  q01: "",
  q02: "",
  q03: "",
  q04: "",
  q05: "",
  q06: "",
  q07: "",
  q08: "",
  q09: "",
  q10: "",
  q11: "",
  q12: "",
  q13: "",
  q14: "",
  q15: "",
};
