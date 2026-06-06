"use client";

import { useEffect } from "react";
import type { ClinicianThreadContext } from "@/lib/clinician-chat-types";
import { ClinicianConsultContextPanel } from "@/components/ClinicianConsultContextPanel";

type ClinicalContextSheetProps = {
  open: boolean;
  onClose: () => void;
  context: ClinicianThreadContext;
  onContextChange: (patch: Partial<ClinicianThreadContext>) => void;
  accessEmail: string;
  onAccessEmailChange: (v: string) => void;
  accessBusy: boolean;
  accessStatus: {
    success: boolean;
    error?: string;
    can_use_pro_clinical_assist?: boolean;
    payment_status?: string;
    verification_status?: string;
  } | null;
  onCheckAccess: () => void;
};

export function ClinicalContextSheet({
  open,
  onClose,
  context,
  onContextChange,
  accessEmail,
  onAccessEmailChange,
  accessBusy,
  accessStatus,
  onCheckAccess,
}: ClinicalContextSheetProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="clinical-sheet-root" role="presentation">
      <button type="button" className="clinical-sheet-backdrop" aria-label="닫기" onClick={onClose} />
      <div
        className="clinical-sheet-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="clinical-context-sheet-title"
      >
        <header className="clinical-sheet-header">
          <h2 id="clinical-context-sheet-title">환자 맥락 · 설정</h2>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            닫기
          </button>
        </header>
        <div className="clinical-sheet-body">
          <ClinicianConsultContextPanel
            compact
            context={context}
            onContextChange={onContextChange}
            accessEmail={accessEmail}
            onAccessEmailChange={onAccessEmailChange}
            accessBusy={accessBusy}
            accessStatus={accessStatus}
            onCheckAccess={onCheckAccess}
          />
        </div>
      </div>
    </div>
  );
}
