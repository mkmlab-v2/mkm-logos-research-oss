/**
 * Consumer-facing A·Code 12 public lexicon — OPSEC smoke screen.
 * Internal MAI codes (MAI-01..12) stay in API/JSON; do not expose 사상·명리·MBTI on consumer surfaces.
 * SSOT mirror: docs/final/artifacts/gtm_mai_copy_bundles_v1.json (public_brand_ko / disclaimer_ko)
 */

export const CONSUMER_ACODE12_PUBLIC_LEXICON_V1 = {
  brandKo: "A·Code 12",
  productLabelKo: "A·Code 12 패턴 스냅샷",
  hubCardSublabelKo:
    "실행·회복·인지 패턴 참고 설문 · 성격검사·임상·투자 판단 아님",
  disclaimerKo:
    "[HYPO] A·Code 12 스냅샷은 실행·회복·인지 패턴 참고용입니다. 성격검사·임상·투자 판단을 대체하지 않습니다.",
} as const;
