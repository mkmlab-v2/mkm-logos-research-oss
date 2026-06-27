/** Human-facing display helpers for Logos Studio (strip boilerplate, improve scan). */

export function stripStudioBoilerplate(text: string): string {
  return (text || "")
    .replace(/^\[HYPO\]\s*/i, "")
    .replace(/\s*why_question_assembled=false\.?\s*/gi, " ")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

export function formatPathStepHuman(step: string): string {
  const s = step.trim();
  if (s.startsWith("node:")) {
    const id = s.slice(5);
    if (/^lemma_/.test(id)) return `원어 앵커 · ${id.replace(/^lemma_/, "")}`;
    if (/^function_/.test(id)) return `기능 · ${id.replace(/^function_/, "").replace(/_/g, " ")}`;
    if (/^concept:/.test(id)) return `개념 · ${id.replace(/^concept:/, "")}`;
    return id.replace(/_/g, " ");
  }
  if (/^[A-Za-z0-9]+\.\d+\.\d+/.test(s)) return s;
  return s.replace(/_/g, " ");
}

export function verseRefShortList(refs: string[], cap = 12): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const r of refs) {
    const t = r.trim();
    if (!t || seen.has(t)) continue;
    seen.add(t);
    out.push(t);
    if (out.length >= cap) break;
  }
  return out;
}

/** Antigravity scriptorium inquiry — topic pills from preset id / slot metadata. */
export function buildScriptoriumTopicPills(
  presetId: string,
  slotLabelKo?: string | null,
): Array<{ id: string; label: string; active?: boolean }> {
  const id = presetId.toLowerCase();
  const pills: Array<{ id: string; label: string; active?: boolean }> = [];

  if (id.includes("job")) {
    pills.push({ id: "ot", label: "구약", active: true });
    pills.push({ id: "book", label: "욥기", active: true });
  } else if (id.includes("isaiah")) {
    pills.push({ id: "ot", label: "구약", active: true });
    pills.push({ id: "book", label: "이사야", active: true });
  } else if (id.includes("gen") || id.includes("nephilim") || id.includes("bigset")) {
    pills.push({ id: "ot", label: "구약", active: true });
  } else if (id.includes("ezra") || id.includes("rev")) {
    pills.push({ id: "ot", label: "구약·신약", active: true });
  }

  if (slotLabelKo) {
    pills.push({ id: "slot", label: slotLabelKo, active: true });
  } else {
    pills.push({ id: "commentary", label: "주석", active: false });
    pills.push({ id: "theology", label: "신학 논문", active: false });
  }

  return pills.slice(0, 5);
}

/** Antigravity mockup — fixed Korean thinking rail (not raw node ids). */
export const SCRIPTORIUM_THINKING_LABELS_KO = [
  "주제 탐색",
  "주요 구절 분석",
  "주석가 의견 검토",
  "신학적 통합",
] as const;

export function buildScriptoriumThinkingSteps(): Array<{ id: string; label: string }> {
  return SCRIPTORIUM_THINKING_LABELS_KO.map((label, index) => ({
    id: `scriptorium-thinking-${index}`,
    label,
  }));
}

export type ScriptoriumReportSection = {
  id: string;
  title: string;
  paragraphs: string[];
  bullets: string[];
};

const SCRIPTORIUM_FALLBACK_SECTION_TITLES = [
  "연구 요약",
  "경로·구절 관측",
  "신학적 함의",
] as const;

function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?…])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Left inquiry panel — short lead, not the full report body. */
export function buildScriptoriumInquirySummary(text: string, maxChars = 320): string {
  const clean = stripStudioBoilerplate(text);
  if (clean.length <= maxChars) return clean;
  const cut = clean.slice(0, maxChars);
  const lastSpace = cut.lastIndexOf(" ");
  return `${(lastSpace > 180 ? cut.slice(0, lastSpace) : cut).trim()}…`;
}

/** Right panel — markdown-ish ### sections or paragraph chunks. */
export function buildScriptoriumReportSections(input: {
  answer: string;
  path?: { note_ko?: string | null };
  insight_card?: { gap_ko?: string; one_liner_ko?: string } | null;
}): ScriptoriumReportSection[] {
  const answer = (input.answer || "").replace(/\r\n/g, "\n").trim();
  const parsed: ScriptoriumReportSection[] = [];
  let current: ScriptoriumReportSection | null = null;

  for (const rawLine of answer.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    const heading = line.match(/^#{2,4}\s*(?:\d+\.\s*)?(.+)$/);
    if (heading) {
      if (current) parsed.push(current);
      current = {
        id: `section-${parsed.length}`,
        title: stripStudioBoilerplate(heading[1]),
        paragraphs: [],
        bullets: [],
      };
      continue;
    }
    const bullet = line.match(/^[-*•]\s+(.+)$/);
    if (bullet) {
      if (!current) {
        current = {
          id: `section-${parsed.length}`,
          title: SCRIPTORIUM_FALLBACK_SECTION_TITLES[0],
          paragraphs: [],
          bullets: [],
        };
      }
      current.bullets.push(stripStudioBoilerplate(bullet[1]));
      continue;
    }
    if (!current) {
      current = {
        id: `section-${parsed.length}`,
        title: SCRIPTORIUM_FALLBACK_SECTION_TITLES[0],
        paragraphs: [],
        bullets: [],
      };
    }
    current.paragraphs.push(stripStudioBoilerplate(line));
  }
  if (current) parsed.push(current);

  if (parsed.length > 0) {
    return parsed.map((section, index) => ({
      ...section,
      title: /^\d+\./.test(section.title) ? section.title : `${index + 1}. ${section.title}`,
    }));
  }

  const body = stripStudioBoilerplate(answer);
  const note = stripStudioBoilerplate(input.path?.note_ko || "");
  const gap = stripStudioBoilerplate(input.insight_card?.gap_ko || input.insight_card?.one_liner_ko || "");
  const sentences = splitSentences(body);
  const chunkSize = Math.max(2, Math.ceil(sentences.length / 3));
  const chunks: string[][] = [];
  for (let i = 0; i < sentences.length; i += chunkSize) {
    chunks.push(sentences.slice(i, i + chunkSize));
  }
  while (chunks.length < 2 && body) {
    chunks.push([]);
  }

  const sections: ScriptoriumReportSection[] = chunks.slice(0, 3).map((chunk, index) => ({
    id: `fallback-${index}`,
    title: `${index + 1}. ${SCRIPTORIUM_FALLBACK_SECTION_TITLES[index] ?? "분석"}`,
    paragraphs: chunk.length ? [chunk.join(" ")] : [],
    bullets: [],
  }));

  if (note && sections[1]) {
    sections[1].paragraphs.push(note);
  } else if (note) {
    sections.push({
      id: "fallback-note",
      title: "2. 경로·구절 관측",
      paragraphs: [note],
      bullets: [],
    });
  }

  if (gap) {
    const target = sections[2] ?? sections[sections.length - 1];
    if (target) {
      target.bullets.push(gap);
    }
  }

  return sections.filter((s) => s.paragraphs.length || s.bullets.length);
}
