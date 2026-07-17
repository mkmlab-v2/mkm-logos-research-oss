import { LogosResearchAskFlowDiagram } from "@/components/logos-research/LogosResearchAskFlowDiagram";
import { LogosResearchAskPageBody } from "@/components/logos-research/LogosResearchAskPageBody";
import { LogosResearchCtaStrip } from "@/components/logos-research/LogosResearchCtaStrip";
import { LogosResearchFooter } from "@/components/logos-research/LogosResearchFooter";
import { LogosResearchJemaOsHandoffBadge } from "@/components/logos-research/LogosResearchJemaOsHandoffBadge";
import { LogosResearchSiteChrome } from "@/components/logos-research/LogosResearchSiteChrome";
import { logosResearchCopy } from "@/content/logosResearchCopy";

const c = logosResearchCopy;
const ask = "ask" in c && c.ask ? c.ask : null;

type AskHeroCopy = {
  eyebrow?: string;
  title?: string;
  lead?: string;
  cta_samples?: string;
};

/** P2: skip BetaStrip on Ask — brand line already carries identity once. */
export default function LogosResearchAskPage() {
  const a = ask as AskHeroCopy | null;
  return (
    <div
      className="logos-research-page logos-research-ask-page"
      data-logos-design="editorial-instrument-v1"
    >
      <LogosResearchSiteChrome active="ask" />
      <main id="main" className="lr-ask-main">
        <span
          hidden
          data-mkm-logos-ask-trust-v1="citation-lock-strip post-feedback-v1"
          aria-hidden="true"
        />
        <section className="lr-ask-hero lr-ask-hero--vp" aria-labelledby="lr-ask-title">
          <p className="lr-eyebrow">{a?.eyebrow ?? "Public Beta · 성경 연구 Ask"}</p>
          <h1 id="lr-ask-title">{a?.title ?? "질문하면, 인용·학파·경로 리포트"}</h1>
          <p className="lr-hero-lead lr-prose">
            {a?.lead ??
              "한 문장만 넣어도 구절 근거를 고정하고 학파별 해석·경로를 한 리포트로 정리합니다."}
          </p>
          <div className="lr-ask-hero-cta">
            <a className="lr-btn lr-btn-primary" href="#lr-ask-composer">
              질문하기
            </a>
            <a className="lr-btn lr-btn-ghost" href="#lr-ask-samples-anchor">
              {a?.cta_samples ?? "샘플 질문 보기"}
            </a>
          </div>
          <LogosResearchJemaOsHandoffBadge />
        </section>
        <div className="lr-ask-flow-inline">
          <LogosResearchAskFlowDiagram />
        </div>
        <LogosResearchAskPageBody />
        <LogosResearchCtaStrip compact />
      </main>
      <LogosResearchFooter />
    </div>
  );
}
