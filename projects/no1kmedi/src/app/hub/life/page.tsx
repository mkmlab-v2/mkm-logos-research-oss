import { UniverseHubPluginPanel } from "@/components/shell/UniverseHubPluginPanel";
import { UniverseLifeBenefitsV2 } from "@/components/shell/UniverseLifeBenefitsV2";
import { UniverseMkmlifeEmbedV2 } from "@/components/shell/UniverseMkmlifeEmbedV2";
import { isMkmlifeEmbedEnabled } from "@/lib/universeHubMkmlifeEmbedV2";
import { buildMkmlifeAskOneHubDeepLink, UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

export const metadata = {
  title: "라이프 케어 — JEMA AI Hub",
};

type PageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

function readPrefill(searchParams?: PageProps["searchParams"]): string | undefined {
  const raw = searchParams?.prefill;
  return typeof raw === "string" ? raw : undefined;
}

export default function HubLifePage({ searchParams }: PageProps) {
  const prefill = readPrefill(searchParams);
  const embedOn = isMkmlifeEmbedEnabled();

  return (
    <div className="universe-hub-plugin-stack">
      <UniverseMkmlifeEmbedV2 prefill={prefill} />
      <UniverseHubPluginPanel
        pluginId="mkm_life"
        title="라이프 케어"
        body={
          embedOn
            ? "로컬 dev pair 또는 NEXT_PUBLIC_UNIVERSE_HUB_MKMLIFE_EMBED=1 — mkmlife iframe이 Hub light chrome 안에 표시됩니다."
            : "웰니스·관측 카드 덱과 원퀘스천은 mkmlife.com consumer_portal_v1에서 운영됩니다."
        }
        primaryCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.mkmlifeHome,
          label: "MKM LIFE 홈으로",
          external: true,
        }}
        secondaryCta={{
          href: buildMkmlifeAskOneHubDeepLink({ prefill }),
          label: "원퀘스천 작성 (오픈 베타)",
          external: true,
        }}
        phaseNote={embedOn ? "P4 · embed ON" : "P4 · deep-link default"}
      />
      <section aria-labelledby="life-benefits-heading">
        <h2 id="life-benefits-heading" className="universe-hub-section-title">
          소비자 면 혜택
        </h2>
        <UniverseLifeBenefitsV2 />
      </section>
    </div>
  );
}
