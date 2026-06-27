import { HubPrefillBannerV2 } from "@/components/shell/HubPrefillBannerV2";
import { UniverseHubPluginPanel } from "@/components/shell/UniverseHubPluginPanel";
import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";
import { MYEONGNI_RESEARCH_STUDIO } from "@/lib/universeHubMyeongniCommercialV1";

export const metadata = {
  title: "명리 관측소 — JEMA AI Hub",
};

type Props = {
  searchParams?: { prefill?: string };
};

export default function HubMyeongniPage({ searchParams }: Props) {
  const prefill = searchParams?.prefill;
  const studioHref = prefill?.trim()
    ? `${MYEONGNI_RESEARCH_STUDIO}?q=${encodeURIComponent(prefill.trim())}&source=jema_hub_v2`
    : `${MYEONGNI_RESEARCH_STUDIO}?source=jema_hub_v2`;

  return (
    <div className="universe-hub-plugin-stack">
      <HubPrefillBannerV2 prefill={prefill} />
      <UniverseHubPluginPanel
        pluginId="myeongni_observatory"
        title="명리 관측소"
        body="四柱·대운·세운 경로 마인드맵은 B-track research_only [HYPO] 중기 방향 참고입니다. 임상 확정·매매·Track A 게이트와 격리됩니다."
        primaryCta={{
          href: studioHref,
          label: "명리 Studio (경로 마인드맵)",
          external: false,
        }}
        secondaryCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.logosResearchStudio,
          label: "Logos Graph Studio",
          external: false,
        }}
        phaseNote="P2 · verify-lite 엔진 · send_gate HOLD"
      />
      <section className="universe-hub-myeongni-notes" aria-labelledby="myeongni-hub-notes">
        <h2 id="myeongni-hub-notes" className="universe-hub-section-title">
          사용 안내
        </h2>
        <ul className="universe-hub-bullet-list">
          <li>데모 팩 또는 출생 입력 후 엔진 조회 → 방사형 마인드맵</li>
          <li>풀 리포트는 요약·Markdown 미리보기만 — human_confirm 경로와 병행</li>
          <li>성경(Logos) 렌즈와 그래프 슬라이스 합선 없음</li>
        </ul>
      </section>
    </div>
  );
}
