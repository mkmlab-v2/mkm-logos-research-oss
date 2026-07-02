import { readFile } from "node:fs/promises";
import path from "node:path";

import { getSyncGolden200Registry, matchGoldenHubQuery } from "./logosGolden200HubMatchV1";
import { LOGOS_STUDIO_DATA_DIR } from "./logosResearchStudioV1";

export type ReadingPackRow = {
  pack_id: string;
  label_ko: string;
  summary_ko: string;
  card_excerpt_ko?: string;
  utterance_class?: string;
  verse_refs?: string[];
};

export type ReadingPackSlice = {
  schema_version: string;
  query_id: string;
  query_ko: string;
  why_question_assembled?: boolean;
  reading_packs: ReadingPackRow[];
  disclaimer?: { note_ko?: string };
};

/** @deprecated use ReadingPackRow */
export type JobReadingPackRow = ReadingPackRow;
/** @deprecated use ReadingPackSlice */
export type JobReadingPackSlice = ReadingPackSlice;

type SliceRegistryEntry = {
  fileName: string;
  queryId: string;
  introLineKo: string;
};

const SLICE_REGISTRY: SliceRegistryEntry[] = [
  {
    fileName: "job_reading_pack_slice_v1.json",
    queryId: "job_suffering_why",
    introLineKo:
      "「왜 고난?」 인과 단답 없음(why_question_assembled=false). 아래 Pack별 읽기 프레임만 제시합니다.",
  },
  {
    fileName: "isaiah_youtube_reading_pack_slice_v1.json",
    queryId: "isaiah_youtube_16chapter",
    introLineKo:
      "66=66 1:1 압축·단일 독해 단정 없음. 아래 Pack별 spine 읽기 프레임만 제시합니다 [NON_GATING].",
  },
  {
    fileName: "gen2_eve_reading_pack_slice_v1.json",
    queryId: "gen2_eve_creation_symbol",
    introLineKo:
      "「갈비/측에서 하와」 상징·비유·원어·학파·4D·자동 concordance — Pack 6종 병렬 [NON_GATING].",
  },
  {
    fileName: "passion_crown_reading_pack_slice_v1.json",
    queryId: "passion_crown_symbol",
    introLineKo:
      "가시면류관 수난 서사 — 복음서 앵커(Matt/Mark/John) Pack 3종 병렬 [NON_GATING].",
  },
  {
    fileName: "antichrist_666_reading_pack_slice_v1.json",
    queryId: "antichrist_666_symbol",
    introLineKo:
      "666·적그리스도 — 계시록·요한서신·데살로니가후서 앵커 Pack 3종 병렬 [NON_GATING].",
  },
  {
    fileName: "rev21_new_creation_reading_pack_slice_v1.json",
    queryId: "rev21_new_creation",
    introLineKo:
      "Rev 21 새 하늘·새 땅 — 종말·위로 서사 Pack 3종 병렬 · Job/666 stub 합선 금지 [NON_GATING].",
  },
];

const PRESET_TO_SLICE_FILE: Record<string, string> = {
  job_job_suffering_reason: "job_reading_pack_slice_v1.json",
  job_existential_suffering: "job_reading_pack_slice_v1.json",
  isaiah_youtube_spine_v1: "isaiah_youtube_reading_pack_slice_v1.json",
  topic_gen_2_anchor: "gen2_eve_reading_pack_slice_v1.json",
};

const CONFLICT_GROUP_TO_SLICE_FILE: Record<string, string> = {
  MKM_CONCEPT_JOB_SUFFERING: "job_reading_pack_slice_v1.json",
  MKM_CONCEPT_ISAIAH_YOUTUBE: "isaiah_youtube_reading_pack_slice_v1.json",
};

const sliceCache = new Map<string, ReadingPackSlice>();

function registryEntry(fileName: string): SliceRegistryEntry | undefined {
  return SLICE_REGISTRY.find((e) => e.fileName === fileName);
}

export async function loadReadingPackSlice(fileName: string): Promise<ReadingPackSlice | null> {
  if (sliceCache.has(fileName)) {
    return sliceCache.get(fileName) ?? null;
  }
  const filePath = path.join(LOGOS_STUDIO_DATA_DIR, fileName);
  try {
    const raw = await readFile(filePath, "utf8");
    const slice = JSON.parse(raw) as ReadingPackSlice;
    sliceCache.set(fileName, slice);
    return slice;
  } catch {
    return null;
  }
}

/** @deprecated use loadReadingPackSlice("job_reading_pack_slice_v1.json") */
export async function loadJobReadingPackSlice(): Promise<ReadingPackSlice | null> {
  return loadReadingPackSlice("job_reading_pack_slice_v1.json");
}

function truncateExcerpt(text: string, maxChars = 1100): string {
  const clean = text.replace(/\r\n/g, "\n").trim();
  if (clean.length <= maxChars) return clean;
  const cut = clean.slice(0, maxChars);
  const lastBreak = cut.lastIndexOf("\n");
  const trimmed = (lastBreak > 200 ? cut.slice(0, lastBreak) : cut).trim();
  return `${trimmed}…`;
}

/** Build scriptorium-friendly markdown from reading pack cards. */
export function buildReadingPackScriptoriumAnswer(
  slice: ReadingPackSlice,
  query: string,
  introLineKo?: string,
): string {
  const entry = SLICE_REGISTRY.find((e) => e.queryId === slice.query_id);
  const intro =
    introLineKo ||
    entry?.introLineKo ||
    "아래 Pack별 읽기 프레임만 제시합니다 [NON_GATING].";
  const lines: string[] = [
    `[HYPO] ${slice.query_ko || query} — reading pack ${slice.reading_packs.length}종 병렬.`,
    intro,
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

function hubSliceFileName(hubId: string): string {
  return `${hubId}_reading_pack_slice_v1.json`;
}

function resolveSliceFileName(
  presetId: string | null | undefined,
  readingPackQueryId: string | null | undefined,
  conflictGroupId?: string | null,
  query?: string,
): string | null {
  if (query) {
    const hub = matchGoldenHubQuery(query, getSyncGolden200Registry());
    if (hub?.hub_id === "antichrist_666") {
      return "antichrist_666_reading_pack_slice_v1.json";
    }
    if (hub?.hub_id === "passion_crown") {
      return "passion_crown_reading_pack_slice_v1.json";
    }
    if (hub?.reading_pack_artifact) {
      return hubSliceFileName(hub.hub_id);
    }
  }
  if (conflictGroupId && CONFLICT_GROUP_TO_SLICE_FILE[conflictGroupId]) {
    return CONFLICT_GROUP_TO_SLICE_FILE[conflictGroupId];
  }
  if (presetId && PRESET_TO_SLICE_FILE[presetId]) {
    return PRESET_TO_SLICE_FILE[presetId];
  }
  if (readingPackQueryId) {
    const byQuery = SLICE_REGISTRY.find((e) => e.queryId === readingPackQueryId.trim());
    if (byQuery) return byQuery.fileName;
  }
  return null;
}

export async function resolveReadingPackAnswerForPreset(
  presetId: string | null | undefined,
  readingPackQueryId: string | null | undefined,
  query: string,
  conflictGroupId?: string | null,
): Promise<string | null> {
  const sliceFile = resolveSliceFileName(presetId, readingPackQueryId, conflictGroupId, query);
  if (!sliceFile) return null;

  const slice = await loadReadingPackSlice(sliceFile);
  if (!slice?.reading_packs?.length) return null;

  const entry = registryEntry(sliceFile);
  const queryId = readingPackQueryId?.trim();
  if (queryId && slice.query_id !== queryId && !conflictGroupId && !presetId) {
    return null;
  }

  return buildReadingPackScriptoriumAnswer(slice, query, entry?.introLineKo);
}
