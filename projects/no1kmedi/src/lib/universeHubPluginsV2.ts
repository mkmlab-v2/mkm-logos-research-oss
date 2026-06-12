/**
 * universe_hub_v2 sidebar plugins — SSOT mirror of
 * docs/final/artifacts/mkm_universe_hub_shell_contract_v2_draft.json
 * Phase 1: deep-link routing only; no backend lane merge.
 */

export const UNIVERSE_HUB_SHELL_ID = "universe_hub_v2" as const;

export type UniverseHubPluginId =
  | "discover"
  | "governed_customization"
  | "oracle_observatory"
  | "mkm_life"
  | "a_code_sandbox"
  | "my_reports"
  | "showroom"
  | "clinician"
  | "operator_wtt";

export type UniverseHubNavGroup = "discover" | "b2b" | "consumer" | "ops";

export type UniverseHubPluginV2 = {
  id: UniverseHubPluginId;
  labelKo: string;
  href: string;
  external?: boolean;
  internalOnly?: boolean;
  laneNote?: string;
  navGroup: UniverseHubNavGroup;
};

export const UNIVERSE_HUB_NAV_GROUP_LABELS: Record<Exclude<UniverseHubNavGroup, "discover">, string> = {
  b2b: "B2B · 가드",
  consumer: "소비자 · 관측",
  ops: "운영 (internal)",
};

const MKMLIFE = "https://mkmlife.com";
const JEMAAI = "https://jemaai.cloud";
const ACODE = "https://a-codeai.com";

export const UNIVERSE_HUB_PLUGINS_V2: UniverseHubPluginV2[] = [
  {
    id: "discover",
    labelKo: "홈 · 발견",
    href: "/hub",
    navGroup: "discover",
  },
  {
    id: "governed_customization",
    labelKo: "AI 맞춤·가드 (B2B)",
    href: "/hub/customize",
    laneNote: "Governed AI Customization · Track C [DRAFT]",
    navGroup: "b2b",
  },
  {
    id: "a_code_sandbox",
    labelKo: "개발자 샌드박스",
    href: "/hub/developer",
    laneNote: "B2B API",
    navGroup: "b2b",
  },
  {
    id: "oracle_observatory",
    labelKo: "오라클 관측소",
    href: "/hub/oracle",
    laneNote: "B-track · research_only",
    navGroup: "consumer",
  },
  {
    id: "mkm_life",
    labelKo: "라이프 케어",
    href: "/hub/life",
    laneNote: "consumer_portal_v1",
    navGroup: "consumer",
  },
  {
    id: "my_reports",
    labelKo: "내 리포트",
    href: "/hub/reports",
    navGroup: "consumer",
  },
  {
    id: "showroom",
    labelKo: "공개 관측 보드",
    href: JEMAAI,
    external: true,
    navGroup: "consumer",
  },
  {
    id: "clinician",
    labelKo: "한의사 보조",
    href: "/clinician",
    laneNote: "clinical_isolated",
    navGroup: "consumer",
  },
  {
    id: "operator_wtt",
    labelKo: "운영자 패널",
    href: "/hub/operator",
    internalOnly: true,
    laneNote: "operator_panel · SEND HOLD",
    navGroup: "ops",
  },
];

const ACODE_OPEN_BENCH_REPRODUCE =
  "https://github.com/mkmlab-v2/a-codeai-compression-reproduce";

export const UNIVERSE_HUB_DEEP_LINKS = {
  mkmlifeHome: MKMLIFE,
  mkmlifeAskOne: `${MKMLIFE}/ask-one`,
  mkmlifeReports: `${MKMLIFE}/my-reports`,
  mkmlifeNewsDeck: `${MKMLIFE}/news-deck`,
  jemaaiShowroom: JEMAAI,
  aCodeLanding: ACODE,
  aCodeOpenBenchReproduce: ACODE_OPEN_BENCH_REPRODUCE,
  clinicianPortal: "https://clinic.no1kmedi.com/",
  enterpriseWttPersonaOs: "/enterprise#wtt-persona-os",
  compressionPilotApply: "/enterprise/apply",
  wttPersonaOsDemo: "https://personadiary.com/wtt-persona-os-demo-v1.html",
} as const;

export function visibleUniverseHubPlugins(): UniverseHubPluginV2[] {
  const showOperator = process.env.NEXT_PUBLIC_UNIVERSE_HUB_OPERATOR_PANEL === "1";
  return UNIVERSE_HUB_PLUGINS_V2.filter((p) => !p.internalOnly || showOperator);
}

export function pluginById(id: UniverseHubPluginId): UniverseHubPluginV2 | undefined {
  return UNIVERSE_HUB_PLUGINS_V2.find((p) => p.id === id);
}
