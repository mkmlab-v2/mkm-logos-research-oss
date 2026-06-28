import { readFile } from "node:fs/promises";
import path from "node:path";

import { LOGOS_STUDIO_DATA_DIR } from "./logosResearchStudioV1";

export type JobReadingPackRow = {
  pack_id: string;
  label_ko: string;
  summary_ko: string;
  card_excerpt_ko?: string;
  utterance_class?: string;
};

export type JobReadingPackSlice = {
  schema_version: string;
  query_id: string;
  query_ko: string;
  why_question_assembled?: boolean;
  reading_packs: JobReadingPackRow[];
  disclaimer?: { note_ko?: string };
};

let sliceCache: JobReadingPackSlice | null = null;

export async function loadJobReadingPackSlice(): Promise<JobReadingPackSlice | null> {
  if (sliceCache) return sliceCache;
  const filePath = path.join(LOGOS_STUDIO_DATA_DIR, "job_reading_pack_slice_v1.json");
  try {
    const raw = await readFile(filePath, "utf8");
    sliceCache = JSON.parse(raw) as JobReadingPackSlice;
    return sliceCache;
  } catch {
    return null;
  }
}

function truncateExcerpt(text: string, maxChars = 520): string {
  const clean = text.replace(/\r\n/g, "\n").trim();
  if (clean.length <= maxChars) return clean;
  const cut = clean.slice(0, maxChars);
  const lastBreak = cut.lastIndexOf("\n");
  const trimmed = (lastBreak > 200 ? cut.slice(0, lastBreak) : cut).trim();
  return `${trimmed}…`;
}

/** Build scriptorium-friendly markdown from reading pack cards (step 3). */
export function buildReadingPackScriptoriumAnswer(
  slice: JobReadingPackSlice,
  query: string,
): string {
  const lines: string[] = [
    `[HYPO] ${slice.query_ko || query} — reading pack ${slice.reading_packs.length}종 병렬.`,
    "「왜 고난?」 인과 단답 없음(why_question_assembled=false). 아래 Pack별 읽기 프레임만 제시합니다.",
  ];

  slice.reading_packs.forEach((pack, index) => {
    lines.push("");
    lines.push(`### ${index + 1}. ${pack.label_ko}`);
    if (pack.summary_ko) {
      lines.push(pack.summary_ko);
    }
    const excerpt = pack.card_excerpt_ko?.trim();
    if (excerpt) {
      lines.push("");
      lines.push(truncateExcerpt(excerpt));
    }
  });

  lines.push("");
  lines.push(
    "단일 Pack·단일 학파 단정 아님 — citation lock·경로 마인드맵과 함께 확인하세요 [NON_GATING].",
  );
  return lines.join("\n");
}

export async function resolveReadingPackAnswerForPreset(
  presetId: string | null | undefined,
  jobReadingPackPresetId: string | null | undefined,
  query: string,
  conflictGroupId?: string | null,
): Promise<string | null> {
  const jobConflict = conflictGroupId === "MKM_CONCEPT_JOB_SUFFERING";
  const jobPreset =
    presetId === "job_job_suffering_reason" ||
    presetId === "job_existential_suffering" ||
    Boolean(jobReadingPackPresetId);
  if (!jobPreset && !jobConflict) return null;

  const slice = await loadJobReadingPackSlice();
  if (!slice?.reading_packs?.length) return null;

  const queryId = jobReadingPackPresetId?.trim();
  if (queryId && slice.query_id !== queryId && !jobConflict && !jobPreset) {
    return null;
  }

  return buildReadingPackScriptoriumAnswer(slice, query);
}
