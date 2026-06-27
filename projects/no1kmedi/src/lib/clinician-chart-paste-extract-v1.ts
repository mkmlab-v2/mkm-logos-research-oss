/**
 * Paste Chart Omni-box — local regex/heuristic metadata extract (no LLM).
 */

import { buildChiefComplaintFromPaste, parseIntakePasteText } from "@/lib/clinician-intake-paste-v1";

export type PasteExtractConfidenceV1 = "high" | "low";

export type PasteExtractDraftV1 = {
  schema: "paste_extract_draft_v1";
  display_name?: string;
  birthdate?: string;
  sex?: "M" | "F" | "unknown";
  age_years?: number;
  chief_complaint?: string;
  confidence: PasteExtractConfidenceV1;
  sources: string[];
};

const NAME_LABEL_RE = /(?:환자명|성명|이름|환자)\s*[:：]\s*([가-힣○●◯〇]{2,4})/;
const NAME_WITH_SEX_RE = /([가-힣]{2,3}[○●◯〇]?)\s*(?:\/|,|\s)\s*(\d{1,3})\s*(?:세|M|F|남|여)/;
const ISO_DATE_RE = /^(19|20)(\d{2})-(\d{2})-(\d{2})$/;
const CC_SECTION_RE = /\[CC\]\s*([^\n\[]+)/i;
const BIRTH_FULL_RE = /(19|20)(\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]?\s*(\d{1,2})?/;
const BIRTH_YEARSUFFIX_RE = /(?:^|[^\d])(\d{2})년생(?:\s*(남|여|남성|여성))?/;
const AGE_RE = /만\s*(\d{1,3})\s*세|(\d{1,3})\s*세\s*(남|여|남성|여성)?/;
const SEX_RE = /(남성|여성|남자|여자|남|여)(?!\w)/;

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function normalizeBirthdate(y: number, m: number, d: number): string | undefined {
  if (y < 1900 || y > 2100 || m < 1 || m > 12 || d < 1 || d > 31) return undefined;
  return `${y}-${pad2(m)}-${pad2(d)}`;
}

function inferBirthYearFromAge(age: number): number | undefined {
  const now = new Date();
  const y = now.getFullYear() - age;
  if (y < 1900 || y > now.getFullYear()) return undefined;
  return y;
}

function parseSexToken(token?: string): "M" | "F" | undefined {
  if (!token) return undefined;
  if (/남|M/i.test(token)) return "M";
  if (/여|F/i.test(token)) return "F";
  return undefined;
}

function parseSlashHeaderLine(line: string): {
  name?: string;
  birthdate?: string;
  sex?: "M" | "F";
  age?: number;
  chief_complaint?: string;
  source?: string;
} | null {
  const trimmed = line.trim();
  if (!trimmed.includes("/")) return null;
  const parts = trimmed.split("/").map((p) => p.trim()).filter(Boolean);
  if (parts.length < 3) return null;
  if (!/^[가-힣]{2,4}$/.test(parts[0]!)) return null;

  let birthdate: string | undefined;
  let sex: "M" | "F" | undefined;
  let age: number | undefined;
  const tail: string[] = [];

  for (const part of parts.slice(1)) {
    const iso = ISO_DATE_RE.exec(part);
    if (!birthdate && iso) {
      birthdate = normalizeBirthdate(
        Number(`${iso[1]}${iso[2]}`),
        Number(iso[3]),
        Number(iso[4]),
      );
      continue;
    }

    const birthHit = extractBirthdate(part);
    if (!birthdate && birthHit.birthdate) {
      birthdate = birthHit.birthdate;
      continue;
    }

    const ageMatch = /^(\d{1,3})\s*세$/.exec(part);
    if (ageMatch) {
      age = Number(ageMatch[1]);
      continue;
    }

    const sexToken = parseSexToken(part);
    if (!sex && sexToken) {
      sex = sexToken;
      continue;
    }

    tail.push(part);
  }

  return {
    name: parts[0],
    birthdate,
    sex,
    age,
    chief_complaint: tail.join(" / ").trim() || undefined,
    source: trimmed,
  };
}

function extractDisplayName(text: string): { name?: string; source?: string } {
  const firstLine = text.split("\n")[0]?.trim() ?? "";
  const slash = parseSlashHeaderLine(firstLine);
  if (slash?.name) return { name: slash.name, source: slash.source };

  const label = NAME_LABEL_RE.exec(text);
  if (label?.[1]) return { name: label[1].trim(), source: label[0] };

  const inline = NAME_WITH_SEX_RE.exec(text);
  if (inline?.[1]) return { name: inline[1].trim(), source: inline[0] };

  return {};
}

function extractBirthdate(text: string): { birthdate?: string; source?: string } {
  const full = BIRTH_FULL_RE.exec(text);
  if (full) {
    const century = full[1];
    const yy = Number(full[2]);
    const y = Number(`${century}${pad2(yy)}`);
    const m = Number(full[3]);
    const d = full[4] ? Number(full[4]) : 1;
    const birthdate = normalizeBirthdate(y, m, d);
    if (birthdate) return { birthdate, source: full[0] };
  }

  const suffix = BIRTH_YEARSUFFIX_RE.exec(text);
  if (suffix?.[1]) {
    const yy = Number(suffix[1]);
    const y = yy >= 0 && yy <= 30 ? 2000 + yy : 1900 + yy;
    const birthdate = normalizeBirthdate(y, 1, 1);
    if (birthdate) return { birthdate, source: suffix[0] };
  }

  return {};
}

function extractAge(text: string): { age?: number; sex?: "M" | "F"; source?: string } {
  const m = AGE_RE.exec(text);
  if (!m) return {};
  const age = Number(m[1] || m[2]);
  if (!Number.isFinite(age) || age < 1 || age > 120) return {};
  const sex = parseSexToken(m[3]);
  return { age, sex, source: m[0] };
}

function extractSex(text: string): { sex?: "M" | "F"; source?: string } {
  const m = SEX_RE.exec(text);
  if (!m?.[1]) return {};
  const sex = parseSexToken(m[1]);
  return sex ? { sex, source: m[0] } : {};
}

export function birthdateToBirthInstantUtc(birthdate: string, ianaTz = "Asia/Seoul"): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(birthdate.trim());
  if (!m) return null;
  const tz = ianaTz.trim() || "Asia/Seoul";
  const d = new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  if (tz === "Asia/Seoul") {
    return new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00+09:00`).toISOString();
  }
  return d.toISOString();
}

export function mergePasteExtractDraft(
  base: PasteExtractDraftV1,
  overrides: Partial<PasteExtractDraftV1>,
): PasteExtractDraftV1 {
  const merged: PasteExtractDraftV1 = {
    ...base,
    ...overrides,
    schema: "paste_extract_draft_v1",
    sources: overrides.sources ?? base.sources,
    confidence: overrides.confidence ?? base.confidence,
  };
  if (merged.display_name || merged.birthdate || (merged.age_years && merged.sex !== "unknown")) {
    merged.confidence = "high";
  } else if (merged.display_name || merged.chief_complaint) {
    merged.confidence = "low";
  }
  return merged;
}

export function formatPasteExtractChipLabel(draft: PasteExtractDraftV1): string {
  const parts: string[] = [];
  parts.push(draft.display_name?.trim() || "?");
  if (draft.birthdate) {
    parts.push(draft.birthdate);
  } else if (draft.age_years) {
    parts.push(`만${draft.age_years}세`);
  } else {
    parts.push("?");
  }
  const sex =
    draft.sex === "M" ? "M" : draft.sex === "F" ? "F" : "?";
  parts.push(sex);
  const cc = draft.chief_complaint?.trim();
  if (cc) parts.push(cc.length > 18 ? `${cc.slice(0, 18)}…` : cc);
  return parts.join(" / ");
}

export function extractChiefComplaintFromPaste(text: string): string | undefined {
  const cc = CC_SECTION_RE.exec(text);
  if (cc?.[1]?.trim()) return cc[1].trim().slice(0, 800);

  const firstLine = text.split("\n")[0]?.trim() ?? "";
  const slash = parseSlashHeaderLine(firstLine);
  if (slash?.chief_complaint) return slash.chief_complaint.slice(0, 800);

  const body =
    slash && text.includes("\n")
      ? text.replace(/\r\n/g, "\n").split("\n").slice(1).join("\n").trim()
      : text;

  const chief = buildChiefComplaintFromPaste(body || text);
  if (slash && chief === firstLine) return slash.chief_complaint?.slice(0, 800);
  return chief || undefined;
}

const TAGGED_SECTION_RE = /\[([A-Za-z가-힣]+)\]\s*([^\n\[]+)/g;

const SITUATION_TAG_KEYS = new Set(["주소", "ADDR", "ADDRESS", "거주", "지역", "LOCATION"]);

function collectTaggedSections(raw: string): Array<{ tag: string; body: string }> {
  const out: Array<{ tag: string; body: string }> = [];
  for (const match of raw.matchAll(TAGGED_SECTION_RE)) {
    const tag = String(match[1] || "").trim();
    const body = String(match[2] || "").trim();
    if (tag && body) out.push({ tag, body });
  }
  return out;
}

function isSituationTag(tag: string): boolean {
  const upper = tag.toUpperCase();
  if (SITUATION_TAG_KEYS.has(tag) || SITUATION_TAG_KEYS.has(upper)) return true;
  return tag.includes("주소");
}

export function buildStructuredIntakeFromPaste(text: string): {
  symptoms: string[];
  situation: string;
  subjective_notes: string;
} {
  const raw = text.replace(/\r\n/g, "\n").trim();
  const draft = extractPasteChartDraftV1(raw);
  const paste = parseIntakePasteText(raw);
  const firstLine = raw.split("\n")[0]?.trim() ?? "";
  const slashHeader = parseSlashHeaderLine(firstLine);
  const tagged = collectTaggedSections(raw);

  const ccTagged = tagged.find((t) => t.tag.toUpperCase() === "CC");
  const chief = (ccTagged?.body || draft.chief_complaint || "").trim();
  const symptoms: string[] = chief ? [chief.slice(0, 500)] : [];

  const situationParts: string[] = [];
  if (draft.display_name) situationParts.push(draft.display_name);
  if (draft.birthdate) situationParts.push(draft.birthdate);
  if (draft.sex === "M") situationParts.push("남");
  else if (draft.sex === "F") situationParts.push("여");
  if (draft.age_years) situationParts.push(`${draft.age_years}세`);
  for (const { tag, body } of tagged) {
    if (isSituationTag(tag)) situationParts.push(body.slice(0, 200));
  }
  const situation = situationParts.length ? situationParts.join(" · ") : paste.situation;

  const noteLines: string[] = [];
  for (const { tag, body } of tagged) {
    if (tag.toUpperCase() === "CC" || isSituationTag(tag)) continue;
    noteLines.push(`[${tag}] ${body}`.slice(0, 500));
  }

  const bodyLines =
    slashHeader && raw.includes("\n") ? raw.split("\n").slice(1) : raw.split("\n").slice(1);
  for (const line of bodyLines) {
    const trimmed = line.trim();
    if (!trimmed || /^\[[A-Za-z가-힣]+\]/.test(trimmed)) continue;
    noteLines.push(trimmed.slice(0, 500));
  }
  const subjective_notes = noteLines.join("\n").trim().slice(0, 8000);

  if (symptoms.length || subjective_notes || situationParts.length) {
    return { symptoms, situation, subjective_notes };
  }

  return {
    symptoms: paste.symptoms,
    situation: situation || paste.situation,
    subjective_notes: paste.subjective_notes,
  };
}

export function extractPasteChartDraftV1(text: string): PasteExtractDraftV1 {
  const raw = text.replace(/\r\n/g, "\n").trim();
  const sources: string[] = [];

  if (!raw) {
    return {
      schema: "paste_extract_draft_v1",
      confidence: "low",
      sources: [],
    };
  }

  const nameHit = extractDisplayName(raw);
  if (nameHit.source) sources.push(nameHit.source);

  const firstLine = raw.split("\n")[0]?.trim() ?? "";
  const slashHeader = parseSlashHeaderLine(firstLine);

  const birthHit = extractBirthdate(raw);
  if (birthHit.source) sources.push(birthHit.source);

  const ageHit = extractAge(raw);
  if (ageHit.source) sources.push(ageHit.source);

  const sexHit = extractSex(raw);
  if (sexHit.source) sources.push(sexHit.source);

  let birthdate = slashHeader?.birthdate || birthHit.birthdate;
  if (!birthdate && ageHit.age) {
    const y = inferBirthYearFromAge(ageHit.age);
    if (y) birthdate = normalizeBirthdate(y, 1, 1);
  }

  const sex = slashHeader?.sex || ageHit.sex || sexHit.sex || "unknown";
  const ageYears = slashHeader?.age ?? ageHit.age;
  const chief = extractChiefComplaintFromPaste(raw);

  let confidence: PasteExtractConfidenceV1 = "low";
  if (nameHit.name && birthdate) confidence = "high";
  else if (nameHit.name && ageYears && sex !== "unknown") confidence = "high";
  else if (nameHit.name || birthdate || chief) confidence = "low";

  return {
    schema: "paste_extract_draft_v1",
    display_name: nameHit.name,
    birthdate,
    sex,
    age_years: ageYears,
    chief_complaint: chief || undefined,
    confidence,
    sources,
  };
}
