"use client";

type Props = {
  requestId: string;
  validationOk?: boolean;
  syndromeHypothesis?: string;
  caution?: string;
};

export function ClinicianCanvasCitationLockPanel({
  requestId,
  validationOk,
  syndromeHypothesis,
  caution,
}: Props) {
  return (
    <aside
      className="clinician-canvas-citation-lock"
      data-clinician-citation-lock="1"
      data-clinician-citation-request-id={requestId}
      data-clinician-citation-validation={validationOk ? "ok" : "pending"}
      aria-label="CDS 봉투 잠금"
    >
      <header className="clinician-canvas-citation-lock-head">
        <p className="clinician-canvas-citation-lock-eyebrow">CDS ENVELOPE LOCK</p>
        <h3 className="clinician-canvas-citation-lock-title">encounter · {requestId}</h3>
      </header>
      <div className="clinician-canvas-citation-lock-block">
        <h4>검증</h4>
        <p>{validationOk ? "km_cds.validation.ok" : "초안 — 한의사 최종 확정 전"}</p>
      </div>
      {syndromeHypothesis ? (
        <div className="clinician-canvas-citation-lock-block">
          <h4>증후 가설</h4>
          <p>{syndromeHypothesis}</p>
        </div>
      ) : null}
      {caution ? (
        <div className="clinician-canvas-citation-lock-block clinician-canvas-citation-lock-block--caution">
          <h4>주의</h4>
          <p>{caution}</p>
        </div>
      ) : null}
      <p className="clinician-canvas-citation-lock-governance">
        [NON_GATING] 보조 초안 · 자동 확정·처방 아님
      </p>
    </aside>
  );
}
