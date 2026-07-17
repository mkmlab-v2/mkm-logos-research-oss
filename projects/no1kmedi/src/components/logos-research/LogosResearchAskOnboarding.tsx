"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { logosResearchCopy } from "@/content/logosResearchCopy";

const DISMISS_KEY = "lr_ask_onboarding_dismissed_v1";

type Step = { title: string; body: string };

/** Strip leading "1. "/"2." so badge + title never double-number (P1 layout audit). */
function stepTitlePlain(title: string): string {
  return title.replace(/^\s*\d+[.)]\s*/, "").trim() || title;
}

export function LogosResearchAskOnboarding({
  onPickSample,
  onDismiss,
}: {
  onPickSample?: (question: string) => void;
  onDismiss?: () => void;
}) {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    try {
      setDismissed(window.localStorage.getItem(DISMISS_KEY) === "1");
    } catch {
      setDismissed(false);
    }
  }, []);

  const dismiss = useCallback(() => {
    try {
      window.localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* ignore */
    }
    setDismissed(true);
    onDismiss?.();
  }, [onDismiss]);

  const beta =
    "inquiry_beta" in logosResearchCopy && logosResearchCopy.inquiry_beta
      ? logosResearchCopy.inquiry_beta
      : null;
  const steps = (beta && typeof beta === "object" && "how_it_works" in beta
    ? (beta as { how_it_works?: Step[] }).how_it_works
    : []) as Step[];
  const samples =
    "ask" in logosResearchCopy &&
    logosResearchCopy.ask &&
    typeof logosResearchCopy.ask === "object" &&
    "sample_questions" in logosResearchCopy.ask
      ? ((logosResearchCopy.ask as { sample_questions?: string[] }).sample_questions ?? [])
      : [];
  const issuesUrl =
    beta && typeof beta === "object" && "github_issues" in beta
      ? String((beta as { github_issues?: string }).github_issues || "")
      : "";

  if (dismissed || !steps.length) return null;

  return (
    <section className="lr-ask-onboarding" aria-labelledby="lr-ask-onboarding-title">
      <div className="lr-ask-onboarding-head">
        <h2 id="lr-ask-onboarding-title">질문 → 인용 → 학파 → 리포트</h2>
        <button type="button" className="lr-ask-onboarding-dismiss" onClick={dismiss}>
          닫기
        </button>
      </div>
      <ol className="lr-ask-onboarding-steps">
        {steps.map((step, i) => {
          const title = stepTitlePlain(step.title);
          return (
            <li key={step.title} style={{ animationDelay: `${i * 60}ms` }}>
              <span className="lr-ask-onboarding-num" aria-hidden="true">
                {i + 1}
              </span>
              <div>
                <strong>{title}</strong>
                <p>{step.body}</p>
              </div>
            </li>
          );
        })}
      </ol>
      {samples.length ? (
        <div className="lr-ask-onboarding-samples" role="group" aria-label="첫 질문 예시">
          <p className="lr-ask-muted">첫 질문 예시 — 클릭하면 바로 분석합니다</p>
          <div className="lr-ask-samples">
            {samples.slice(0, 3).map((sample) => (
              <button
                key={sample}
                type="button"
                className="lr-ask-sample-chip"
                onClick={() => onPickSample?.(sample)}
              >
                {sample}
              </button>
            ))}
          </div>
        </div>
      ) : null}
      <div className="lr-ask-onboarding-links">
        <Link className="lr-btn lr-btn-ghost" href="/logos-research/docs/how-it-works">
          작동 방식
        </Link>
        {issuesUrl ? (
          <a className="lr-btn lr-btn-ghost" href={issuesUrl} target="_blank" rel="noopener noreferrer">
            GitHub 피드백
          </a>
        ) : null}
      </div>
    </section>
  );
}
