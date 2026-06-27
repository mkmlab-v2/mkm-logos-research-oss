/** no1kmedi.com apex — 대국민 한의학 AI (v1 copy + storage keys). */

export const NATIONAL_KM_ASK_V1 = {
  schema: "no1kmedi_national_km_ask_v1",
  version: "0.1.0",
  product_name_ko: "no1kmedi 한의학 AI",
  disclaimer_ko:
    "본 답변은 한의학 이해·생활관리 참고용이며, 진단·처방·응급 판단을 대체하지 않습니다. 증상이 심하거나 급격히 악화되면 즉시 의료기관을 이용해 주세요.",
} as const;

export const NATIONAL_KM_ASK_STORAGE_KEY = "mkm_national_km_ask_turns_v1";
export const NATIONAL_KM_ASK_DISCLAIMER_KEY = "mkm_national_km_ask_disclaimer_ack_v1";

export const NATIONAL_KM_STARTER_PROMPTS = [
  "소화가 자주 안 좋을 때 한의학에서는 어떻게 봐요?",
  "불면과 피로가 같이 있을 때 생활에서 조절할 점은?",
  "한약은 누구에게 맞나요? 일반인이 알아야 할 주의점은?",
  "어깨·허리 통증을 한의학적으로 이해하려면?",
] as const;
