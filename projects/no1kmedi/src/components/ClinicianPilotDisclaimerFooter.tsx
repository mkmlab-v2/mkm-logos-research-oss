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
        <span className="clinician-pilot-footer-tag">[HYPO] 참고</span>
        참고·초안용 도구이며 의료기기·원격진료가 아닙니다. artifact·게이트 연결 시에만 보조 초안을 제공합니다.
        최종 진단·처방·기록은 한의사가 확정합니다.
        명리·보조 슬롯은 비게이팅 참고용입니다.{" "}
        <button type="button" className="clinician-pilot-footer-link" onClick={onOpenSafety}>
          안전·고지 전문 보기
        </button>
      </div>
    </footer>
  );
}
