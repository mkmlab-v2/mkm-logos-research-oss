import { formatSasangInternalLabel } from "@/lib/clinician-simple-copilot-v1";

const SASANG_KO_HINTS: Array<{ re: RegExp; code: string }> = [
  { re: /태음|taeeum|taeum/i, code: "taeeum" },
  { re: /소양|soyang|soyag/i, code: "soyang" },
  { re: /소음|soeum/i, code: "soeum" },
  { re: /태양|taeyang/i, code: "taeyang" },
];

export function inferSasangCandidateFromLabel(label: string): string {
  const t = label.trim();
  if (!t) return "unknown";
  for (const hint of SASANG_KO_HINTS) {
    if (hint.re.test(t)) return hint.code;
  }
  return "unknown";
}

export function resolveSasangLabelForFusion(chartText: string, override?: string): string | undefined {
  const trimmed = override?.trim();
  if (trimmed && trimmed !== "미입력") return trimmed;
  const code = inferSasangCandidateFromLabel(chartText);
  return formatSasangInternalLabel(code) || undefined;
}
