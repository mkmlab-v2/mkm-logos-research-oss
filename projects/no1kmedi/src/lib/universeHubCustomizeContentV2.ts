/**
 * Static copy for /hub/customize — mirrors governed_ai_customization_* SSOT (no runtime fetch).
 */

export type CustomizePackageTier = "core" | "proof" | "upsell";

export type CustomizePackageRow = {
  id: string;
  tier: CustomizePackageTier;
  labelKo: string;
  buyerValueKo: string;
};

export type CustomizePillar = {
  id: string;
  titleKo: string;
  summaryKo: string;
  artifactPath: string;
  ctaHref: string;
  ctaLabelKo: string;
};

export type CustomizeSpoke = {
  id: string;
  label: string;
  href: string;
  external?: boolean;
  tag?: string;
};

export const CUSTOMIZE_HEADLINE_KO =
  "Governed AI Customization — 극한 대화에서도 붕괴하지 않는 페르소나·안전 레이어";

export const CUSTOMIZE_SUBHEAD_KO =
  "프롬프트 튜닝이 아니라 EPB 밴드·대화 위험 FSM·감사 가능 인입으로 도메인 맞춤. 압축(비용)·매크로(관측)는 선택 스포크.";

export const CUSTOMIZE_SPOKES: CustomizeSpoke[] = [
  {
    id: "compression",
    label: "Compression",
    href: "/enterprise/apply",
    tag: "Tier-0 감사 신청",
  },
  {
    id: "macro",
    label: "Macro",
    href: "/hub/oracle",
    tag: "[HYPO] 관측",
  },
  {
    id: "showroom",
    label: "Showroom",
    href: "https://jemaai.cloud/public_observe_v1.html",
    external: true,
    tag: "공개 관측",
  },
];

export const CUSTOMIZE_PILLARS: CustomizePillar[] = [
  {
    id: "epb",
    titleKo: "EPB 밴드",
    summaryKo: "따뜻함·경계 트리거 프로필로 톤 드리프트 억제",
    artifactPath: "reports/wtt_dialog_risk_policy_tune_v1_latest.json",
    ctaHref: "/enterprise#wtt-persona-os",
    ctaLabelKo: "Persona OS 개요",
  },
  {
    id: "fsm",
    titleKo: "Dialog FSM",
    summaryKo: "normal → elevated → cooldown → human handoff",
    artifactPath: "reports/wtt_spicy_corpus_fsm_batch_v1_latest.json",
    ctaHref: "/enterprise#wtt-persona-os",
    ctaLabelKo: "FSM·스트레스 개요",
  },
  {
    id: "audit",
    titleKo: "Audit intake",
    summaryKo: "마스킹·stub·합성 스트레스 — SEND HOLD",
    artifactPath: "data/wtt/examples/wtt_customer_masked_stub_v1.example.jsonl",
    ctaHref: "/enterprise/apply",
    ctaLabelKo: "토큰 압축 사전 감사 신청",
  },
];

export const CUSTOMIZE_PACKAGES: CustomizePackageRow[] = [
  {
    id: "core_persona_guard",
    tier: "core",
    labelKo: "Core — Persona Guard",
    buyerValueKo: "프로필·FSM·과부하 스캔·쿨다운·테넌트 manifest",
  },
  {
    id: "proof_stress_certified",
    tier: "proof",
    labelKo: "Proof — Stress Certified",
    buyerValueKo: "합성 spicy + stub + FSM before/after (조건부·합성 라벨)",
  },
  {
    id: "spoke_compression_adapter",
    tier: "upsell",
    labelKo: "+Cost — Compression Adapter",
    buyerValueKo: "동일 가드 페르소나를 토큰·미터링으로 운영 (Track A 별도 게이트)",
  },
  {
    id: "spoke_macro_radar",
    tier: "upsell",
    labelKo: "+Radar — Macro Insight",
    buyerValueKo: "B-track 경보·관측 — 봇 트리거·실매매 합선 없음",
  },
];

export const CUSTOMIZE_ICP_LABELS: string[] = [
  "웰니스 B2B2C 규제",
  "에듀테크 AI 튜터",
  "프리미엄 CS",
  "SI·화이트라벨",
];
