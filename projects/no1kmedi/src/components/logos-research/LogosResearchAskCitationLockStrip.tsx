"use client";

import { citationLockVerseTitle, type PublicCitationLockModelV1 } from "@/lib/logosInquiryAskDisplayV1";

export function LogosResearchAskCitationLockStrip({ model }: { model: PublicCitationLockModelV1 }) {
  return (
    <section className="lr-ask-citation-lock" aria-label="출처 고정">
      <div className="lr-ask-citation-lock-head">
        <h3>출처 고정</h3>
      </div>
      <p className="lr-ask-muted lr-ask-citation-lock-note">
        통찰 본문 전에 참고 구절을 먼저 고정합니다. 교리·투자 단정이 아닌 연구 참고용입니다.
      </p>
      {model.verseRefs.length ? (
        <ul className="lr-ask-citation-lock-refs" aria-label="고정 구절">
          {model.verseRefs.map((ref) => (
            <li key={ref}>
              <span
                className="lr-ask-citation-lock-ref-chip"
                title={citationLockVerseTitle(ref)}
                tabIndex={0}
              >
                {ref}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
