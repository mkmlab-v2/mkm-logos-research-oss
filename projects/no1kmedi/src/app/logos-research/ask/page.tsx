import { LogosResearchAskPageBody } from "@/components/logos-research/LogosResearchAskPageBody";
import { LogosResearchBetaStrip } from "@/components/logos-research/LogosResearchBetaStrip";
import { LogosResearchFooter } from "@/components/logos-research/LogosResearchFooter";
import { LogosResearchJemaOsHandoffBadge } from "@/components/logos-research/LogosResearchJemaOsHandoffBadge";
import { LogosResearchSiteChrome } from "@/components/logos-research/LogosResearchSiteChrome";
import { logosResearchCopy } from "@/content/logosResearchCopy";
import { DEFAULT_HOMEPAGE_PRESET, homepagePresetClassMap } from "@/lib/homepagePreset";

const c = logosResearchCopy;
const presetClass = homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET];
const ask = "ask" in c && c.ask ? c.ask : null;

export default function LogosResearchAskPage() {
  return (
    <div className={`${presetClass} logos-research-page logos-research-ask-page`}>
      <LogosResearchSiteChrome active="ask" />
      <LogosResearchBetaStrip />
      <main id="main" className="lr-ask-main">
        <span
          hidden
          data-mkm-logos-ask-trust-v1="citation-lock-strip post-feedback-v1"
          aria-hidden="true"
        />
        <section className="lr-ask-hero" aria-labelledby="lr-ask-title">
          <p className="lr-eyebrow">{ask?.eyebrow ?? "Public Beta · 성경 Q&A"}</p>
          <h1 id="lr-ask-title">{ask?.title ?? "성경·텍스트 Q&A"}</h1>
          <p className="lr-hero-lead">
            {ask?.lead ??
              "질문 → citation lock · 학파 비교 · lemma 메타 — 텍스트 리포트 JSON. 그래픽·Studio 제외."}
          </p>
          <LogosResearchJemaOsHandoffBadge />
        </section>
        <LogosResearchAskPageBody />
      </main>
      <LogosResearchFooter />
    </div>
  );
}
