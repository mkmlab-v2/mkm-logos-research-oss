"use client";

type ClinicianPilotDisclaimerFooterProps = {
  onOpenSafety: () => void;
};

/** Pilot commercial — PUBLIC_FACING §3 Silver/non-medical aligned compact footer. */
export function ClinicianPilotDisclaimerFooter({ onOpenSafety }: ClinicianPilotDisclaimerFooterProps) {
  return (
    <footer className="clinician-pilot-footer" role="contentinfo" aria-label="안전·면책 고지">
      <div className="clinician-pilot-footer-inner">
        <span className="clinician-pilot-footer-tag">CDSS 보조</span>
        참고·초안용 · 최종 판단은 한의사 확정.{" "}
        <button type="button" className="clinician-pilot-footer-link" onClick={onOpenSafety}>
          안전·고지 전문 보기
        </button>
      </div>
    </footer>
  );
}
