import { logosResearchCopy } from "@/content/logosResearchCopy";

type BetaCopy = {
  github_issues?: string;
  github_repo?: string;
  feedback_cta?: string;
};

type CtaCopy = {
  title?: string;
  ask?: string;
  samples?: string;
  github?: string;
  docs?: string;
};

/**
 * Next-step CTA strip — Try Ask · Samples · GitHub · Docs.
 * No arxiv / "Read Paper" for unrelated governance thesis.
 */
export function LogosResearchCtaStrip({ compact = false }: { compact?: boolean }) {
  const c = logosResearchCopy;
  const beta =
    "inquiry_beta" in c && c.inquiry_beta ? (c.inquiry_beta as BetaCopy) : null;
  const strip =
    "cta_strip" in c && c.cta_strip ? (c.cta_strip as CtaCopy) : null;

  return (
    <aside
      className={`lr-cta-strip${compact ? " lr-cta-strip--compact" : ""}`}
      aria-label={strip?.title ?? "다음 행동"}
      data-logos-cta-strip="1"
    >
      {!compact ? (
        <p className="lr-cta-strip-title">{strip?.title ?? "다음에 할 일"}</p>
      ) : null}
      <div className="lr-cta-strip-actions">
        <a className="lr-btn lr-btn-primary" href="/logos-research/ask">
          {strip?.ask ?? c.hero?.cta_primary ?? "베타 Q&A 시작"}
        </a>
        <a className="lr-btn lr-btn-ghost" href="/logos-research#inquiry">
          {strip?.samples ?? "샘플 질문"}
        </a>
        {beta?.github_issues ? (
          <a
            className="lr-btn lr-btn-ghost"
            href={beta.github_issues}
            target="_blank"
            rel="noopener noreferrer"
          >
            {strip?.github ?? beta.feedback_cta ?? "GitHub 피드백"}
          </a>
        ) : null}
        <a className="lr-btn lr-btn-ghost" href="/logos-research/docs/how-it-works">
          {strip?.docs ?? "작동 방식"}
        </a>
      </div>
    </aside>
  );
}
