export function formatIntakePinInput(value: string): string {
  const normalized = value.replace(/[^A-Z0-9]/gi, "").toUpperCase().slice(0, 6);
  if (normalized.length <= 3) return normalized;
  return `${normalized.slice(0, 3)}-${normalized.slice(3)}`;
}

export function triageBadgeClass(level: "routine" | "priority" | "emergency"): string {
  return `triage-badge triage-badge-${level}`;
}

export function triageLabel(level: "routine" | "priority" | "emergency"): string {
  if (level === "routine") return "일반";
  if (level === "priority") return "우선";
  return "응급";
}

export function normalizePatientNameInput(value: string): string {
  return value.replace(/\s+/g, " ").trimStart();
}

export function normalizePhoneLast4Input(value: string): string {
  return value.replace(/\D/g, "").slice(0, 4);
}

/** Map API error codes to clinician-facing Korean copy. */
export function formatPatientPinLookupError(error?: string): string {
  switch (error) {
    case "second_factor_required":
      return "환자 이름 또는 연락처 뒤 4자리를 함께 입력해 주세요. (PIN만으로는 조회할 수 없습니다)";
    case "pin_required":
      return "문진 코드(PIN)를 입력해 주세요.";
    case "pin_not_found_or_mismatch":
      return "PIN·이름(또는 전화 뒤 4자리)이 일치하지 않습니다. 환자가 입력한 이름과 같은지 확인해 주세요.";
    case "too_many_lookup_attempts":
      return "조회 시도가 많습니다. 잠시 후 다시 시도해 주세요.";
    default:
      return error ? `조회 실패: ${error}` : "조회에 실패했습니다.";
  }
}
