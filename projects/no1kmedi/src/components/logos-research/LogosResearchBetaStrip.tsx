import { logosResearchCopy } from "@/content/logosResearchCopy";

type BetaCopy = {
  badge?: string;
  tagline_ko?: string;
  github_repo?: string;
  github_issues?: string;
  feedback_cta?: string;
};

export function LogosResearchBetaStrip() {
  const beta =
    "inquiry_beta" in logosResearchCopy && logosResearchCopy.inquiry_beta
      ? (logosResearchCopy.inquiry_beta as BetaCopy)
      : null;
  if (!beta) return null;

  return (
    <aside className="lr-beta-strip" role="status" aria-label="Public Beta">
      <span className="lr-beta-badge">{beta.badge ?? "Public Beta"}</span>
      <span className="lr-beta-tagline">{beta.tagline_ko}</span>
      {beta.github_issues ? (
        <a className="lr-beta-feedback" href={beta.github_issues} target="_blank" rel="noopener noreferrer">
          {beta.feedback_cta ?? "GitHub 피드백"}
        </a>
      ) : null}
    </aside>
  );
}
