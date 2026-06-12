import { readFile } from "node:fs/promises";
import path from "node:path";

import { HubPrefillBannerV2 } from "@/components/shell/HubPrefillBannerV2";
import { UniverseHubPluginPanel } from "@/components/shell/UniverseHubPluginPanel";
import { UniverseOracleDeckV2 } from "@/components/shell/UniverseOracleDeckV2";
import { UniverseOracleRq025CardV2 } from "@/components/shell/UniverseOracleRq025CardV2";
import type { UniverseHubRq025OracleCardV1 } from "@/lib/universeHubRq025OracleCardV1";
import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

export const metadata = {
  title: "오라클 관측소 — JEMA AI Hub",
};

async function loadRq025Card(): Promise<UniverseHubRq025OracleCardV1 | null> {
  try {
    const filePath = path.join(
      process.cwd(),
      "public/data/universe_hub_rq025_oracle_card_v1.json",
    );
    const raw = await readFile(filePath, "utf8");
    const data = JSON.parse(raw) as UniverseHubRq025OracleCardV1;
    if (data.schema !== "universe_hub_rq025_oracle_card_v1") return null;
    return data;
  } catch {
    return null;
  }
}

type Props = {
  searchParams?: { prefill?: string };
};

export default async function HubOraclePage({ searchParams }: Props) {
  const prefill = searchParams?.prefill;
  const rq025Card = await loadRq025Card();
  return (
    <div className="universe-hub-plugin-stack">
      <HubPrefillBannerV2 prefill={prefill} />
      <UniverseHubPluginPanel
        pluginId="oracle_observatory"
        title="오라클 관측소"
        body="시장·환경 관측은 B-track research_only입니다. 헤드라인 벤치 KPI·Track A 수치는 표시하지 않습니다."
        primaryCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.jemaaiShowroom,
          label: "공개 관측 (jemaai.cloud)",
          external: true,
        }}
        secondaryCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.mkmlifeNewsDeck,
          label: "MKM LIFE 관측 덱",
          external: true,
        }}
        phaseNote="P2 · rq025 card + 타임라인"
      />
      {rq025Card ? <UniverseOracleRq025CardV2 card={rq025Card} /> : null}
      <section aria-labelledby="oracle-timeline-heading">
        <h2 id="oracle-timeline-heading" className="universe-hub-section-title">
          관측 레이어 타임라인
        </h2>
        <UniverseOracleDeckV2 />
      </section>
    </div>
  );
}