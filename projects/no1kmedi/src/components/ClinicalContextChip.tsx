"use client";

import type { ClinicianThreadContext } from "@/lib/clinician-chat-types";

export function formatClinicalContextLabel(ctx: ClinicianThreadContext): string {
  const name =
    ctx.loadedSurveyContext?.patientName?.trim() ||
    (ctx.ssotSlug?.trim() ? ctx.ssotSlug.trim() : "") ||
    "환자 미지정";
  const birth = ctx.birthInstantUtc?.trim()
    ? ctx.birthInstantUtc.trim().slice(0, 10)
    : "출생 미입력";
  return `${name} · ${birth}`;
}

type ClinicalContextChipProps = {
  context: ClinicianThreadContext;
  onClick: () => void;
  disabled?: boolean;
};

export function ClinicalContextChip({ context, onClick, disabled }: ClinicalContextChipProps) {
  const label = formatClinicalContextLabel(context);
  const hasPin = Boolean(context.loadedSurveyContext?.intakePin);

  return (
    <button
      type="button"
      className="clinical-context-chip"
      onClick={onClick}
      disabled={disabled}
      aria-label="환자 맥락 편집 — PIN·출생·권한"
      title="클릭하여 환자 PIN·출생·권한 설정"
    >
      <span className="clinical-context-chip-icon" aria-hidden="true">
        👤
      </span>
      <span className="clinical-context-chip-text">{label}</span>
      {hasPin ? <span className="clinical-context-chip-meta">PIN</span> : null}
    </button>
  );
}
