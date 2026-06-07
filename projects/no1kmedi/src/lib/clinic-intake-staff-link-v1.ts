/**
 * Reception desk: patient intake URL + SMS body (PIN only — no clinical detail).
 */

export function buildClinicIntakePublicUrl(origin?: string): string {
  const base = (origin || "").trim().replace(/\/$/, "");
  if (base) return `${base}/intake`;
  return "/intake";
}

export function buildClinicIntakeStaffSmsBody(input: {
  intakeUrl: string;
  intakePin?: string;
  clinicName?: string;
}): string {
  const clinic = (input.clinicName || "한의원").trim();
  const lines = [
    `[${clinic} 사전 문진]`,
    "아래 링크에서 증상·생활습관 설문을 작성해 주세요.",
    "※ 진단·처방이 아닌 접수 보조입니다.",
    input.intakeUrl,
  ];
  if (input.intakePin?.trim()) {
    lines.push("", `작성 후 안내 코드: ${input.intakePin.trim()}`);
  }
  return lines.join("\n");
}

export function buildClinicIntakePatientPinSmsBody(input: { intakePin: string; clinicName?: string }): string {
  const clinic = (input.clinicName || "한의원").trim();
  return [
    `[${clinic} 접수 완료]`,
    `문진 코드: ${input.intakePin.trim()}`,
    "접수 데스크 또는 진료실에 코드를 알려 주세요.",
    "※ 본 문자는 접수 확인용이며 진료 결과가 아닙니다.",
  ].join("\n");
}
