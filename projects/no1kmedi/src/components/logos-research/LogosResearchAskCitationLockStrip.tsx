"use client";

import {
  citationPathLabelKo,
  citationLockVerseTitle,
  type PublicCitationLockModelV1,
} from "@/lib/logosInquiryAskDisplayV1";

export function LogosResearchAskCitationLockStrip({ model }: { model: PublicCitationLockModelV1 }) {
  const pathKo = citationPathLabelKo(model.pathLabel);
  return (
    <section className="lr-ask-citation-lock" aria-label="Citation lock">
      <div className="lr-ask-citation-lock-head">
        <div className="lr-ask-citation-lock-title-row">
          <h3>출처 고정 (Citation lock)</h3>
          <span className="lr-ask-citation-lock-gate">[NON_GATING]</span>
        </div>
        <span className="lr-ask-citation-lock-badge">{pathKo}</span>
      </div>
      <p className="lr-ask-muted lr-ask-citation-lock-note">
        본문 통찰 전에 S1 앵커 구절을 고정합니다. 교리·투자 단정이 아닌 연구 참고용입니다.
      </p>
      {model.presetId || model.hubId ? (
        <p className="lr-ask-citation-lock-meta">
          {model.presetId ? (
            <span>
              Hub preset: <code>{model.presetId}</code>
            </span>
          ) : null}
          {model.hubId ? (
            <span>
              Golden hub: <code>{model.hubId}</code>
            </span>
          ) : null}
        </p>
      ) : null}
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
      {model.anchorCount > 0 ? (
        <p className="lr-ask-muted lr-ask-citation-lock-anchor-note">
          citation lock anchors: {model.anchorCount}
          {model.previewAnchors.length
            ? ` · ${model.previewAnchors.slice(0, 2).join(" · ")}`
            : null}
        </p>
      ) : null}
    </section>
  );
}
