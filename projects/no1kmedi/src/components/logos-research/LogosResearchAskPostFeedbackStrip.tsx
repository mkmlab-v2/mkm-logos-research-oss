"use client";

import { logosResearchCopy } from "@/content/logosResearchCopy";

type BetaCopy = {
  github_issues?: string;
  feedback_cta?: string;
  github_discussions?: string;
};

/** Post-answer beta feedback CTA — Issues template only (no in-app vote API). */
export function LogosResearchAskPostFeedbackStrip({ queryId }: { queryId?: string | null }) {
  const beta =
    "inquiry_beta" in logosResearchCopy && logosResearchCopy.inquiry_beta
      ? (logosResearchCopy.inquiry_beta as BetaCopy)
      : null;
  const issuesUrl = beta?.github_issues?.trim() || "";
  if (!issuesUrl) return null;

  const href = queryId
    ? `${issuesUrl}${issuesUrl.includes("?") ? "&" : "?"}title=${encodeURIComponent(`[beta] Ask feedback · ${queryId}`)}`
    : issuesUrl;

  return (
    <aside className="lr-ask-post-feedback" role="complementary" aria-label="베타 피드백">
      <p className="lr-ask-post-feedback-lead">이 답변이 연구에 도움이 되었나요?</p>
      <p className="lr-ask-muted lr-ask-post-feedback-note">
        교리·투자 조언이 아닌 텍스트 연구 베타입니다. 품질·인용 오류는 Issues로 알려 주세요.
      </p>
      <div className="lr-ask-post-feedback-actions">
        <a className="lr-btn lr-btn-ghost" href={href} target="_blank" rel="noopener noreferrer">
          {beta?.feedback_cta ?? "GitHub Issues · 피드백"}
        </a>
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
      </div>
    </aside>
  );
}
