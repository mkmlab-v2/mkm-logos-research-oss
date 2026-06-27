/**
 * Hub inspector — read-only artifact pointers ([HYPO] / non-gating).
 * Public hrefs are fetchable or routable; repoPath is display-only SSOT.
 */

import { JEMAAI_CLOUD_PUBLIC_OBSERVE_URL } from "@/lib/jemaaiShowroomPublicV1";
import {
  LOGOS_RESEARCH_HOME,
  LOGOS_RESEARCH_STUDIO,
} from "@/lib/universeHubLogosCommercialV1";
import { UNIVERSE_HUB_LOGOS_TOPOLOGY_PATH } from "@/lib/universeHubLogosTopologyV1";

export type HubInspectorArtifactV1 = {
  id: string;
  labelKo: string;
  href: string;
  external?: boolean;
  repoPath?: string;
  hypo?: boolean;
};

export const HUB_INSPECTOR_ARTIFACTS_V1: HubInspectorArtifactV1[] = [
  {
    id: "logos_studio_commercial",
    labelKo: "Graph Studio · 상용 워크스페이스 (on-domain)",
    href: LOGOS_RESEARCH_STUDIO,
    hypo: true,
  },
  {
    id: "logos_research_home",
    labelKo: "Logos Scripture Research (랜딩)",
    href: LOGOS_RESEARCH_HOME,
    hypo: true,
  },
  {
    id: "logos_topology_json",
    labelKo: "Logos 4D topology JSON",
    href: UNIVERSE_HUB_LOGOS_TOPOLOGY_PATH,
    repoPath: "projects/no1kmedi/public/data/logos_corpus_4d_topology_hub_v1.json",
    hypo: true,
  },
  {
    id: "logos_observatory",
    labelKo: "Logos 관측소 (Hub spoke)",
    href: "/hub/logos",
    hypo: true,
  },
  {
    id: "jemaai_showroom",
    labelKo: "jemaai.cloud 공개 관측",
    href: JEMAAI_CLOUD_PUBLIC_OBSERVE_URL,
    external: true,
  },
  {
    id: "positioning_onepager",
    labelKo: "Agentic positioning one-pager (internal)",
    href: "/enterprise",
    repoPath: "docs/final/artifacts/mkm_agentic_engineering_positioning_onepager_v1_latest.md",
  },
  {
    id: "positioning_deck",
    labelKo: "Positioning deck (internal · local PDF)",
    href: "/enterprise",
    repoPath: "docs/final/artifacts/mkm_positioning_deck_v1_latest.pdf",
  },
  {
    id: "open_bench_benchmark",
    labelKo: "A-Code open bench (public)",
    href: "https://a-codeai.com/benchmark/",
    external: true,
    repoPath: "https://github.com/mkmlab-v2/a-codeai-compression-reproduce",
    hypo: true,
  },
];
