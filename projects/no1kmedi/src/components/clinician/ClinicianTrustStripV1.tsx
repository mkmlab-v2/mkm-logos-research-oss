"use client";

type ClinicianTrustStripV1Props = {
  onOpenSafety?: () => void;
};

export function ClinicianTrustStripV1({ onOpenSafety }: ClinicianTrustStripV1Props) {
  return (
    <div className="clinician-trust-strip-v1" role="status">
      <span className="clinician-trust-strip-v1__copy">
        원장 보조 · CDSS · send_gate HOLD · 진단·처방 확정 아님 · Paste Chart=실험 · 본제품=/clinic-trust
      </span>
      <a className="clinician-trust-strip-link" href="/clinic-trust">
        HOLD Q&A
      </a>
      {onOpenSafety ? (
        <button type="button" className="clinician-trust-strip-link" onClick={onOpenSafety}>
          안전·고지
        </button>
      ) : null}
    </div>
  );
}
