import { LogosResearchBetaStrip } from "@/components/logos-research/LogosResearchBetaStrip";
import { LogosResearchDeployContractStrip } from "@/components/logos-research/LogosResearchDeployContractStrip";
import { LogosResearchFooter } from "@/components/logos-research/LogosResearchFooter";
import { LogosResearchHomeInquirySection } from "@/components/logos-research/LogosResearchHomeInquirySection";
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
};

export function LogosResearchInquiryBetaHome() {
  const c = logosResearchCopy;
  const beta =
    "inquiry_beta" in c && c.inquiry_beta ? (c.inquiry_beta as BetaCopy) : null;
  const steps = beta?.how_it_works ?? [];

  return (
    <>
      <LogosResearchBetaStrip />
      <main id="main">
        <section className="lr-hero lr-hero--text-only" aria-labelledby="lr-hero-title">
          <p className="lr-eyebrow">{c.hero.eyebrow}</p>
          <p className="lr-public-url">
            <span>Research</span>
            <a href={c.publicUrl}>{c.publicUrl.replace("https://", "")}</a>
          </p>
          <h1 id="lr-hero-title">
            {c.hero.title.split("\n").map((line, i) => (
              <span key={line}>
                {i > 0 ? <br /> : null}
                {line}
              </span>
            ))}
          </h1>
          <p className="lr-hero-lead">{c.hero.lead}</p>
          <div className="lr-hero-cta">
            <a className="lr-btn lr-btn-primary" href="/logos-research/ask">
              {c.hero.cta_primary}
            </a>
            {beta?.github_issues ? (
              <a
                className="lr-btn lr-btn-ghost"
                href={beta.github_issues}
                target="_blank"
                rel="noopener noreferrer"
              >
                {c.hero.cta_secondary ?? "GitHub 피드백"}
              </a>
            ) : null}
          </div>
        </section>

        <LogosResearchHomeInquirySection />

        <LogosResearchDeployContractStrip />

        {steps.length ? (
          <section id="how" className="lr-section" aria-labelledby="lr-how-title">
            <h2 id="lr-how-title">베타에서 하는 일</h2>
            <ul className="lr-beta-steps">
              {steps.map((step) => (
                <li key={step.title} className="lr-beta-step">
                  <strong>{step.title}</strong>
                  <p>{step.body}</p>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section id="oss" className="lr-section lr-section--alt" aria-labelledby="lr-oss-title">
          <h2 id="lr-oss-title">오픈소스 · 피드백</h2>
          <p className="lr-section-lead">
            {beta?.reproduce_hint ??
              "하네스·pytest는 GitHub에서 재현 가능 — 제품 UI 베타와 OSS 범위는 분리되어 있습니다."}
          </p>
          <div className="lr-hero-cta">
            {beta?.github_repo ? (
              <a
                className="lr-btn lr-btn-primary"
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
            <a className="lr-btn lr-btn-ghost" href="/logos-research/docs/how-it-works">
              작동 방식
            </a>
          </div>
        </section>

        <details className="lr-section lr-studio-deferred">
          <summary>
            <span className="lr-studio-deferred-badge">
              {beta?.studio_deferred_title ?? "Graph Studio (Pro) — 베타 범위 외"}
            </span>
          </summary>
          <p className="lr-section-lead">
            {beta?.studio_deferred_lead ??
              "경로·그래프 시각화는 복잡도상 별도 탭. 베타는 텍스트 Q&A 안정화 우선."}
          </p>
          <a className="lr-btn lr-btn-ghost" href="/logos-research/studio">
            Studio 미리보기 (연구용)
          </a>
        </details>

        <details className="lr-disclaimer-fold lr-section">
          <summary>{c.disclaimer.title}</summary>
          <ul className="lr-disclaimer-list">
            {c.disclaimer.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </details>
      </main>
      <LogosResearchFooter />
    </>
  );
}
