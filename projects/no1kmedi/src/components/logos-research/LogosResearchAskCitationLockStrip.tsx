"use client";

import {
  citationLockVerseTitle,
  citationPathLabelPublicKo,
  citationWhyVerseOneHopKo,
  type PublicCitationLockModelV1,
} from "@/lib/logosInquiryAskDisplayV1";
import { braidRefsEqual } from "@/lib/logosAskTextGraphBraidV1";

type Props = {
  model: PublicCitationLockModelV1;
  /** viewport = soft-open first screen; scholar = same evidence, denser meta */
  variant?: "viewport" | "scholar";
  /** D-VIZ-4: selected citation ↔ graph braid focus */
  braidFocusRef?: string | null;
  onBraidFocusRef?: (ref: string) => void;
};

export function LogosResearchAskCitationLockStrip({
  model,
  variant = "viewport",
  braidFocusRef = null,
  onBraidFocusRef,
}: Props) {
  const refCount = model.verseRefs.length;
  const pathKo = citationPathLabelPublicKo(model.pathLabel);
  const whyOneHop = citationWhyVerseOneHopKo(model);
  const scholar = variant === "scholar";
  const braidOn = Boolean(onBraidFocusRef);

  return (
    <section
      className={`lr-ask-citation-lock lr-ask-citation-lock--viewport${scholar ? " lr-ask-citation-lock--scholar" : ""}`}
      data-lr-ask-citation-viewport="1"
      data-lr-ask-citation-path={model.pathLabel}
      data-lr-ask-citation-refs={String(refCount)}
      data-lr-ask-braid={braidOn ? "1" : undefined}
      data-lr-ask-braid-focus={braidFocusRef || undefined}
      aria-label="근거 구절 · 연구 경로"
    >
      <header className="lr-ask-citation-lock-head">
        <div className="lr-ask-citation-lock-title-row">
          <p className="lr-ask-citation-lock-eyebrow">근거 먼저</p>
          <h3 className="lr-ask-citation-lock-title">출처 고정</h3>
          <span className="lr-ask-citation-lock-badge" data-lr-ask-path-badge="1">
            {pathKo}
          </span>
        </div>
        {refCount > 0 ? (
          <p className="lr-ask-citation-lock-count" aria-hidden="true">
            {refCount}구절
          </p>
        ) : null}
      </header>

      <p className="lr-ask-muted lr-ask-citation-lock-note">
        통찰보다 먼저 보이는 성경 근거입니다.
        {braidOn
          ? " 구절을 누르면 오른쪽 경로 지도에서 같은 노드가 강조됩니다."
          : " 교리·투자 단정이 아닌 연구 참고용입니다."}
      </p>

      {whyOneHop ? (
        <p className="lr-ask-citation-lock-why" data-lr-ask-why-one-hop="1">
          <span className="lr-ask-citation-lock-why-label">왜 이 구절</span>
          <span className="lr-ask-citation-lock-why-body">{whyOneHop}</span>
        </p>
      ) : null}

      {refCount ? (
        <>
          <ul className="lr-ask-citation-lock-refs" aria-label="고정 구절">
            {model.verseRefs.map((ref) => {
              const selected = Boolean(braidFocusRef && braidRefsEqual(braidFocusRef, ref));
              const title = citationLockVerseTitle(ref);
              if (onBraidFocusRef) {
                return (
                  <li key={ref}>
                    <button
                      type="button"
                      className={`lr-ask-citation-lock-ref-chip lr-ask-citation-lock-ref-chip--braid${selected ? " lr-ask-citation-lock-ref-chip--braid-active" : ""}`}
                      title={`${title} · 경로 지도에서 강조`}
                      aria-pressed={selected}
                      data-lr-ask-braid-ref={ref}
                      data-lr-ask-braid-active={selected ? "1" : "0"}
                      onClick={() => onBraidFocusRef(ref)}
                    >
                      {ref}
                    </button>
                  </li>
                );
              }
              return (
                <li key={ref}>
                  <span
                    className="lr-ask-citation-lock-ref-chip"
                    title={title}
                    tabIndex={0}
                  >
                    {ref}
                  </span>
                </li>
              );
            })}
          </ul>
          {refCount > 1 ? (
            <p className="lr-ask-citation-lock-path-trail" data-lr-ask-path-trail="1" aria-label="구절 경로">
              <span className="lr-ask-citation-lock-path-trail-label">경로</span>
              <span className="lr-ask-citation-lock-path-trail-body">
                {model.verseRefs.slice(0, 5).join(" → ")}
                {refCount > 5 ? " → …" : ""}
              </span>
            </p>
          ) : null}
        </>
      ) : (
        <p className="lr-ask-muted">구절 앵커를 모으는 중…</p>
      )}
    </section>
  );
}
