import { readFile } from "node:fs/promises";
import path from "node:path";

import { HubPrefillBannerV2 } from "@/components/shell/HubPrefillBannerV2";
import { UniverseHubPluginPanel } from "@/components/shell/UniverseHubPluginPanel";
import { UniverseLogosObservatoryV2 } from "@/components/shell/UniverseLogosObservatoryV2";
import {
  isLogosTopologyHubV1,
  type LogosTopologyHubV1,
} from "@/lib/universeHubLogosTopologyV1";
import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";
import { LOGOS_RESEARCH_STUDIO } from "@/lib/universeHubLogosCommercialV1";

export const metadata = {
  title: "Logos 관측소 — JEMA AI Hub",
};

async function loadTopology(): Promise<LogosTopologyHubV1 | null> {
  try {
    const filePath = path.join(
      process.cwd(),
      "public/data/logos_corpus_4d_topology_hub_v1.json",
    );
    const raw = await readFile(filePath, "utf8");
    const data = JSON.parse(raw) as unknown;
    return isLogosTopologyHubV1(data) ? data : null;
  } catch {
    return null;
  }
}

type Props = {
  searchParams?: { prefill?: string };
};

export default async function HubLogosPage({ searchParams }: Props) {
  const prefill = searchParams?.prefill;
  const topology = await loadTopology();
  return (
    <div className="universe-hub-plugin-stack">
      <HubPrefillBannerV2 prefill={prefill} />
      <UniverseHubPluginPanel
        pluginId="logos_observatory"
        title="Logos 관측소"
        body="31,102절 닫힌 코퍼스 내부 4D 기하학 스냅샷입니다. 시장 예언·Track A·실매매와 격리된 B-track [HYPO] 관측 레이어입니다."
        primaryCta={{
          href: LOGOS_RESEARCH_STUDIO,
          label: "Graph Studio (상용 · on-domain)",
          external: false,
        }}
        secondaryCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.jemaaiShowroom,
          label: "공개 관측 (jemaai.cloud)",
          external: true,
        }}
        phaseNote="P2 · precomputed JSON · /hub/logos air-gap"
      />
      {topology ? (
        <UniverseLogosObservatoryV2 topology={topology} />
      ) : (
        <p className="universe-hub-logos-missing">
          배치 스냅샷이 없습니다. 루트에서{" "}
          <code>py scripts/build_logos_corpus_4d_topology_v1.py</code> 실행 후 Hub public JSON을
          갱신하세요.
        </p>
      )}
    </div>
  );
}
