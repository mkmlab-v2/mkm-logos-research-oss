import { LogosResearchAskFlowDiagram } from "@/components/logos-research/LogosResearchAskFlowDiagram";
import { LogosResearchBetaStrip } from "@/components/logos-research/LogosResearchBetaStrip";
import { LogosResearchCtaStrip } from "@/components/logos-research/LogosResearchCtaStrip";
import { LogosResearchFooter } from "@/components/logos-research/LogosResearchFooter";
import { LogosResearchHomeInquirySection } from "@/components/logos-research/LogosResearchHomeInquirySection";
import { LogosResearchLandingProductPreview } from "@/components/logos-research/LogosResearchLandingProductPreview";
import { LogosResearchStorySection } from "@/components/logos-research/LogosResearchStorySection";
import { LogosResearchStudioDemoFold } from "@/components/logos-research/LogosResearchStudioDemoFold";
import { logosResearchCopy } from "@/content/logosResearchCopy";

type BetaCopy = {
  badge?: string;
  how_it_works?: Array<{ title: string; body: string }>;
  github_repo?: string;
  github_issues?: string;
  github_discussions?: string;
  oss_cta?: string;
  reproduce_hint?: string;
  studio_deferred_title?: string;
  studio_deferred_lead?: string;
  brand_definition_ko?: string;
};

/**
 * Soft-open landing story:
 * Interest → Problem → Solution → Flow → Examples → Honesty → CTA
 * Keeps L1–L4 product preview; Bible Ask identity only.
 */
export function LogosResearchInquiryBetaHome() {
  const c = logosResearchCopy;
  const beta =
    "inquiry_beta" in c && c.inquiry_beta ? (c.inquiry_beta as BetaCopy) : null;
  const steps = beta?.how_it_works ?? [];
  const brandDef =
    beta?.brand_definition_ko ??
    ("definition_ko" in c.brand && typeof c.brand.definition_ko === "string"
      ? c.brand.definition_ko
      : null);

  return (
    <>
      <LogosResearchBetaStrip />
      <main id="main">
        <section className="lr-hero lr-hero--soft-open" aria-labelledby="lr-hero-title">
          <p className="lr-hero-brand" aria-label="LOGOS">
            {c.brand.productShort}
          </p>
          {brandDef ? <p className="lr-hero-definition">{brandDef}</p> : null}
          <p className="lr-eyebrow">{c.hero.eyebrow}</p>
          <h1 id="lr-hero-title">
            {c.hero.title.split("\n").map((line, i) => (
              <span key={line}>
                {i > 0 ? <br /> : null}
                {line}
              </span>
            ))}
          </h1>
          <p className="lr-hero-lead lr-prose">{c.hero.lead}</p>
          <div className="lr-hero-cta">
            <a className="lr-btn lr-btn-primary" href="/logos-research/ask">
              {c.hero.cta_primary}
            </a>
            <a className="lr-btn lr-btn-ghost" href="#inquiry">
              샘플 질문
            </a>
          </div>
        </section>

        <LogosResearchStorySection />

        <section id="flow" className="lr-section lr-section--alt" aria-labelledby="lr-flow-title">
          <h2 id="lr-flow-title">작동 흐름</h2>
          <p className="lr-section-lead lr-prose">
            질문하면 인용·학파·경로가 한 리포트로 이어집니다. AI 거버넌스 슬로건이 아니라 성경 텍스트 연구 흐름입니다.
          </p>
          <LogosResearchAskFlowDiagram />
          {steps.length ? (
            <ul className="lr-beta-steps">
              {steps.map((step) => (
                <li key={step.title} className="lr-beta-step">
                  <strong>{step.title}</strong>
                  <p className="lr-prose">{step.body}</p>
                </li>
              ))}
            </ul>
          ) : null}
          <p className="lr-section-lead lr-how-docs-link">
            <a href="/logos-research/docs/how-it-works">문서에서 자세히 보기</a>
          </p>
        </section>

        <LogosResearchLandingProductPreview />

        <LogosResearchHomeInquirySection />

        <section
          id="honesty"
          className="lr-section lr-honesty-banner"
          aria-labelledby="lr-honesty-title"
        >
          <h2 id="lr-honesty-title">정직 배너</h2>
          <p className="lr-prose lr-section-lead">
            {beta?.reproduce_hint ??
              "Public Beta · 무료 8회/일 · 결제·회원가입 없음. 가짜 벤치마크·저자·점수를 표시하지 않습니다."}
          </p>
          <ul className="lr-honesty-list">
            <li>버전 · 베타 배지 · 일일 쿼터를 화면에서 확인</li>
            <li>피드백은 GitHub Issues · OSS 하네스는 별도 저장소</li>
            <li>교리 판결·상담 대체·상용 완료 주장 없음 (SEND HOLD)</li>
          </ul>
        </section>

        <LogosResearchCtaStrip />

        <section id="oss" className="lr-section lr-section--alt" aria-labelledby="lr-oss-title">
          <h2 id="lr-oss-title">오픈소스 · 피드백</h2>
          <p className="lr-section-lead lr-prose">
            {beta?.reproduce_hint ??
              "하네스·pytest는 GitHub에서 재현 가능 — 제품 UI 베타와 OSS 범위는 분리되어 있습니다."}
          </p>
          <div className="lr-hero-cta">
            {beta?.github_repo ? (
              <a
                className="lr-btn lr-btn-ghost"
                href={beta.github_repo}
                target="_blank"
                rel="noopener noreferrer"
              >
                {beta.oss_cta ?? "GitHub 저장소"}
              </a>
            ) : null}
            {beta?.github_discussions ? (
              <a
                className="lr-btn lr-btn-ghost"
                href={beta.github_discussions}
                target="_blank"
                rel="noopener noreferrer"
              >
                Discussions
              </a>
            ) : null}
            {beta?.github_issues ? (
              <a
                className="lr-btn lr-btn-primary"
                href={beta.github_issues}
                target="_blank"
                rel="noopener noreferrer"
              >
                {c.hero.cta_secondary ?? "GitHub 피드백"}
              </a>
            ) : null}
          </div>
        </section>

        <LogosResearchStudioDemoFold
          title={beta?.studio_deferred_title ?? "Graph Studio — 베타 후 · OSS 검증 후"}
          lead={
            beta?.studio_deferred_lead ??
            "경로·그래프 시각화는 별도 탭입니다. 지금은 텍스트 Q&A를 먼저 안정화합니다. 결제·회원가입 없음."
          }
        />

        <details className="lr-disclaimer-fold lr-section">
          <summary>{c.disclaimer.title}</summary>
          <ul className="lr-disclaimer-list">
            {c.disclaimer.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </details>

        <LogosResearchCtaStrip compact />
      </main>
      <LogosResearchFooter />
    </>
  );
}
