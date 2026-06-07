/** Plain-language chip options — no constitution jargon for patients. */

export type ClinicIntakeChipOption = { id: string; label: string; value: string };

export const CLINIC_INTAKE_SYMPTOM_CHIPS: ClinicIntakeChipOption[] = [
  { id: "back", label: "허리·골반", value: "허리·골반 불편" },
  { id: "neck", label: "목·어깨", value: "목·어깨 불편" },
  { id: "head", label: "두통·어지럼", value: "두통·어지럼" },
  { id: "sleep", label: "수면·피로", value: "수면·피로" },
  { id: "digest", label: "소화·위장", value: "소화·위장 불편" },
  { id: "stress", label: "스트레스·긴장", value: "스트레스·긴장" },
  { id: "other", label: "직접 입력", value: "__custom__" },
];

export const CLINIC_INTAKE_DURATION_CHIPS: ClinicIntakeChipOption[] = [
  { id: "d3", label: "3일 이내", value: "3일 이내" },
  { id: "w1", label: "약 1주", value: "약 1주" },
  { id: "w4", label: "1주~1개월", value: "1주~1개월" },
  { id: "m1", label: "1개월 이상", value: "1개월 이상" },
];

export const CLINIC_INTAKE_SLEEP_CHIPS: ClinicIntakeChipOption[] = [
  { id: "ok", label: "대체로 잘 잔다", value: "대체로 잘 잔다" },
  { id: "onset", label: "잠들기 어렵다", value: "잠들기 어렵다" },
  { id: "wake", label: "자주 깬다", value: "자주 깬다" },
  { id: "early", label: "새벽에 깬다", value: "새벽에 깬다" },
];

export const CLINIC_INTAKE_DIGESTION_CHIPS: ClinicIntakeChipOption[] = [
  { id: "ok", label: "괜찮다", value: "괜찮다" },
  { id: "bloated", label: "더부룩함", value: "식후 더부룩함" },
  { id: "bowel", label: "설사·변비", value: "설사·변비" },
  { id: "appetite", label: "식욕 없음", value: "식욕 없음" },
];

export const CLINIC_INTAKE_HEAT_COLD_CHIPS: ClinicIntakeChipOption[] = [
  { id: "hot", label: "더위를 더 탄다", value: "더위를 더 탐" },
  { id: "cold", label: "추위를 더 탄다", value: "추위를 더 탐" },
  { id: "same", label: "비슷하다", value: "비슷함" },
];

export const CLINIC_INTAKE_FATIGUE_CHIPS: ClinicIntakeChipOption[] = [
  { id: "fast", label: "쉬면 금방 회복", value: "휴식하면 빠르게 회복" },
  { id: "slow", label: "피로가 오래 간다", value: "휴식해도 오래 감" },
  { id: "mid", label: "보통", value: "중간" },
];

export const CLINIC_INTAKE_WIZARD_STEPS = [
  { id: "basic", title: "기본 정보", hint: "이름·연락처·생년월일만 입력해 주세요." },
  { id: "symptom", title: "불편한 곳", hint: "체질을 몰라도 괜찮아요. 지금 불편한 점만 골라 주세요." },
  { id: "daily", title: "수면·소화", hint: "요즘 생활 패턴을 알려 주세요. 한의사가 참고합니다." },
  { id: "finish", title: "마무리", hint: "동의 후 제출하면 접수 코드(PIN)를 받습니다." },
] as const;

export function painScaleLabel(n: number): string {
  if (n <= 2) return "약함";
  if (n <= 5) return "보통";
  if (n <= 7) return "꽤 불편";
  return "매우 심함";
}
