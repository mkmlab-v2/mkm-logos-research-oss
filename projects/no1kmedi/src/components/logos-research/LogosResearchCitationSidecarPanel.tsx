"use client";

import type { CitationDetailV1 } from "@/lib/logosResearchCitationDetailV1";

type Props = {
  detail: CitationDetailV1;
  onOpenExplore?: () => void;
  onClear?: () => void;
  variant?: "default" | "scriptorium";
};

export function LogosResearchCitationSidecarPanel({
  detail,
  onOpenExplore,
  onClear,
  variant = "default",
}: Props) {
  const scriptorium = variant === "scriptorium";

  return (
    <aside
      className={`lr-studio-citation-sidecar${scriptorium ? " lr-studio-citation-sidecar--scriptorium" : ""}`}
      data-logos-citation-sidecar="1"
      data-logos-citation-title={detail.title}
      data-logos-citation-has-verse-body={detail.verseBodyKo ? "1" : "0"}
      aria-live="polite"
      aria-label={scriptorium ? "인용 잠금" : "선택 구절·노드 해설"}
    >
      <header className="lr-studio-citation-sidecar-head">
        <div>
          <p className="lr-studio-citation-sidecar-eyebrow">
            {scriptorium ? "인용 잠금" : "Citation detail · [HYPO]"}
          </p>
          <h4 className="lr-studio-citation-sidecar-title">{detail.title}</h4>
          {!scriptorium && detail.subtitle ? (
            <p className="lr-studio-citation-sidecar-subtitle">{detail.subtitle}</p>
          ) : null}
        </div>
        <div className="lr-studio-citation-sidecar-actions">
          {scriptorium ? (
            <span className="lr-studio-citation-sidecar-lock" aria-hidden="true">
              🔒
            </span>
          ) : null}
          {onOpenExplore ? (
            <button type="button" className="lr-studio-citation-sidecar-btn" onClick={onOpenExplore}>
              {scriptorium ? "창에서 보기" : "망에서 보기"}
            </button>
          ) : null}
          {onClear ? (
            <button type="button" className="lr-studio-citation-sidecar-btn lr-studio-citation-sidecar-btn--ghost" onClick={onClear}>
              닫기
            </button>
          ) : null}
        </div>
      </header>

      {!scriptorium ? (
        <div className="lr-studio-citation-sidecar-badges">
          {detail.badges.map((b) => (
            <span key={b} className="lr-studio-citation-sidecar-badge">
              {b}
            </span>
          ))}
        </div>
      ) : null}

      {!scriptorium ? <p className="lr-studio-citation-sidecar-role">{detail.pathRole}</p> : null}

      {detail.verseBodyKo ? (
        <section className="lr-studio-citation-sidecar-block lr-studio-citation-sidecar-block--verse">
          {scriptorium ? (
            <h5 className="lr-studio-citation-sidecar-verse-ref">{detail.title}</h5>
          ) : (
            <h5>구절 본문 · 개역개정</h5>
          )}
          <blockquote className="lr-studio-citation-sidecar-verse">{detail.verseBodyKo}</blockquote>
        </section>
      ) : null}

      {!scriptorium && detail.verseContextKo ? (
        <section className="lr-studio-citation-sidecar-block">
          <h5>맥락 · reading pack</h5>
          <p>{detail.verseContextKo}</p>
        </section>
      ) : null}

      {!scriptorium && detail.pathNote ? (
        <section className="lr-studio-citation-sidecar-block">
          <h5>경로 해설</h5>
          <p>{detail.pathNote}</p>
        </section>
      ) : null}

      {detail.pathSteps.length ? (
        <section className="lr-studio-citation-sidecar-block">
          <h5>{scriptorium ? "경로 단계" : "경로 단계"}</h5>
          <ol className="lr-studio-citation-sidecar-steps">
            {detail.pathSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>
      ) : null}

      {!scriptorium && detail.insightLine ? (
        <section className="lr-studio-citation-sidecar-block lr-studio-citation-sidecar-block--insight">
          <h5>경로 요약</h5>
          <p>{detail.insightLine}</p>
        </section>
      ) : null}

      {!scriptorium && detail.answerExcerpt ? (
        <section className="lr-studio-citation-sidecar-block lr-studio-citation-sidecar-block--muted">
          <h5>질의 응답 발췌</h5>
          <p>{detail.answerExcerpt}{detail.answerExcerpt.length >= 280 ? "…" : ""}</p>
        </section>
      ) : null}

      {!scriptorium && detail.governance ? (
        <p className="lr-studio-citation-sidecar-governance">{detail.governance}</p>
      ) : null}
    </aside>
  );
}
