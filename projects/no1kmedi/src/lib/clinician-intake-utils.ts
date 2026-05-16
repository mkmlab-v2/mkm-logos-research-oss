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
