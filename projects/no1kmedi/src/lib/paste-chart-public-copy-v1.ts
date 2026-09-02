/**
 * Paste Chart v1 — 대외·랜딩 카피 SSOT (Track B · research_only)
 * 정합: PUBLIC_FACING §3 · MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1
 * 문서 미러: reports/paste_chart_landing_why_not_auto_charting_copy_v1.md
 */
export const PASTE_CHART_PUBLIC_COPY_V1 = {
  brandSub: "EMR 복붙 · 로컬 SSOT · Track B 초안",
  omniLead:
    "EMR·카톡·메모를 통째로 붙여넣으세요. 이름·생년·주증상은 아래 칩에서 확인·수정합니다.",
  whyNotAutoSummary: "왜 자동 차팅이 아닌가",
  whyNotAutoBullets: [
    "AI는 SOAP·조언 초안만 제안합니다. 환자 맥락과 임상 판단은 원장이 EMR에 직접 기록합니다.",
    "EMR 자동 주입이 아닌 슬롯 복붙 — 누가 확정·기록했는지 경계가 분명합니다.",
    "환자 텍스트는 원내 워크스페이스 로컬 파이프라인만 거칩니다. 해외 SaaS 적재·자동 차팅 기록은 하지 않습니다.",
  ] as const,
  footerDisclaimer:
    "Track B 초안 · 원장 검토·확정 후 EMR 기록 · 진단·처방 확정 아님 · EMR 자동 기록 없음",
  footerDisclaimerSecondary:
    "CDSS 초안은 참고용이며, 최종 판단·기록 책임은 원장에게 있습니다.",
} as const;
