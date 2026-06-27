/**
 * Paste text → patient_intake_fusion_draft_v1 intake fields (Human Gold v0).
 */

export type ParsedIntakePasteV1 = {
  symptoms: string[];
  situation: string;
  subjective_notes: string;
};

const BULLET_RE = /^[\s]*(?:[-*•]|\d+[.)])\s+/;

export function parseIntakePasteText(text: string): ParsedIntakePasteV1 {
  const raw = text.replace(/\r\n/g, "\n").trim();
  if (!raw) {
    return { symptoms: [], situation: "", subjective_notes: "" };
  }

  const lines = raw.split("\n").map((l) => l.trim()).filter(Boolean);
  const symptoms: string[] = [];
  const narrative: string[] = [];

  for (const line of lines) {
    if (BULLET_RE.test(line)) {
      const item = line.replace(BULLET_RE, "").trim();
      if (item) symptoms.push(item.slice(0, 500));
    } else {
      narrative.push(line);
    }
  }

  const situation = (narrative[0] || raw.split("\n")[0] || "").slice(0, 8000);
  const subjective_notes = raw.slice(0, 8000);

  if (symptoms.length === 0 && raw.length < 400) {
    const parts = raw
      .split(/[,，·]/)
      .map((p) => p.trim())
      .filter((p) => p.length > 1);
    if (parts.length >= 2 && parts.length <= 8) {
      return {
        symptoms: parts.map((p) => p.slice(0, 500)),
        situation: parts[0]!.slice(0, 8000),
        subjective_notes,
      };
    }
  }

  return { symptoms, situation, subjective_notes };
}

export function buildChiefComplaintFromPaste(chartText: string): string {
  const paste = parseIntakePasteText(chartText);
  if (paste.situation.trim()) return paste.situation.trim().slice(0, 800);
  if (paste.symptoms.length) return paste.symptoms.join(" · ").slice(0, 800);
  return paste.subjective_notes.trim().slice(0, 800);
}
