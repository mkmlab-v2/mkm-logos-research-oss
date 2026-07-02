/** Query-topic vs path/conflict relevance guard (B-track [HYPO], NON_GATING). */
import {
  hubPrimaryVerseRefs,
  loadGolden200AnchorRegistry,
  matchGoldenHubQuery,
  matchGoldenHubTopic,
  type Golden200HubEntryV1,
} from "./logosGolden200AnchorRegistryV1";
import type { StudioQueryPayload } from "./logosResearchStudioV1";

import { detectPsalm23Topic } from "./logosInquiryTopicDetectV1";

export { detectAntichrist666Topic } from "./logosInquiryVerseThematicV1";
export { detectPsalm23Topic } from "./logosInquiryTopicDetectV1";

const VERSE_REF_RE = /\b([A-Za-z][A-Za-z0-9_]*)\.(\d+)\.(\d+)\b/g;

const GEN6_CONFLICT_IDS = new Set([
  "MKM_CONCEPT_SONS_OF_GOD",
  "MKM_CONCEPT_NEPHILIM",
  "Sons_of_God_Theological_Interpretation",
]);

const JOB_SUFFERING_PRESET_IDS = new Set([
  "job_job_suffering_reason",
  "job_existential_suffering",
]);

const APOCALYPTIC_TOPIC_BOOKS = new Set(["Rev", "1John", "2Thess"]);
const SUFFERING_STUB_BOOKS = new Set(["Job", "Ps", "Jer"]);

export type QueryTopicMismatch = {
  code: string;
  hint_ko: string;
  expected_anchor_verses: string[];
};

function norm(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

function booksFromVerseText(text: string): Set<string> {
  const books = new Set<string>();
  for (const match of text.matchAll(VERSE_REF_RE)) {
    books.add(match[1]);
  }
  return books;
}

function booksFromPath(path: StudioQueryPayload["path"] | undefined): Set<string> {
  const parts: string[] = [];
  for (const ref of path?.verse_refs ?? []) parts.push(String(ref));
  for (const step of path?.steps ?? []) parts.push(String(step));
  return booksFromVerseText(parts.join(" "));
}

function booksFromConflict(conflict: StudioQueryPayload["conflict_context"]): Set<string> {
  const parts: string[] = [];
  for (const group of conflict?.groups ?? []) {
    parts.push(String(group.conflict_group_id ?? ""));
    parts.push(String(group.lexicon_base ?? ""));
    for (const school of group.schools ?? []) {
      for (const ref of school.verse_refs ?? []) parts.push(String(ref));
    }
  }
  return booksFromVerseText(parts.join(" "));
}

function chaptersForBook(
  book: string,
  path: StudioQueryPayload["path"] | undefined,
  conflict: StudioQueryPayload["conflict_context"],
): Set<number> {
  const chapters = new Set<number>();
  const parts: string[] = [];
  for (const ref of path?.verse_refs ?? []) parts.push(String(ref));
  for (const group of conflict?.groups ?? []) {
    for (const school of group.schools ?? []) {
      for (const ref of school.verse_refs ?? []) parts.push(String(ref));
    }
  }
  const re = new RegExp(`^${book}\\.(\\d+)`, "i");
  for (const part of parts) {
    const m = re.exec(part.replace(/\s/g, ""));
    if (m) chapters.add(Number(m[1]));
  }
  return chapters;
}

function detectRegistryHubPathMismatch(
  query: string,
  hub: Golden200HubEntryV1,
  payload: Pick<StudioQueryPayload, "path" | "conflict_context" | "preset_id">,
): QueryTopicMismatch | null {
  const pathBooks = booksFromPath(payload.path);
  const conflictBooks = booksFromConflict(payload.conflict_context);
  const evidenceBooks = new Set([...pathBooks, ...conflictBooks]);

  if (payload.preset_id && hub.blocked_preset_ids?.includes(payload.preset_id)) {
    const expected = hub.expected_books ?? [];
    const hasExpected = expected.length === 0 || expected.some((b) => evidenceBooks.has(b));
    if (!hasExpected) {
      return {
        code: `${hub.hub_id}_vs_blocked_preset`,
        expected_anchor_verses: hub.primary_verse_refs.slice(0, 8),
        hint_ko:
          `질문은 ${hub.hub_id} Hub 맥락인데, 라우터가 차단된 stub 프리셋(${payload.preset_id})을 선택했습니다. ` +
          `${hub.primary_verse_refs.slice(0, 4).join(" · ")} citation lock으로 재질의하세요.`,
      };
    }
  }

  const expectedBooks = hub.expected_books ?? [];
  const blockedStubs = new Set(hub.blocked_stub_books ?? []);
  if (expectedBooks.length && evidenceBooks.size > 0) {
    const hasExpected = [...evidenceBooks].some((b) => expectedBooks.includes(b));
    const stubOnly =
      blockedStubs.size > 0 && [...evidenceBooks].every((b) => blockedStubs.has(b) || b === "Heb" || b === "Dan");
    if (!hasExpected && stubOnly) {
      return {
        code: `${hub.hub_id}_vs_stub_path`,
        expected_anchor_verses: hub.primary_verse_refs.slice(0, 8),
        hint_ko:
          `질문은 ${hub.hub_id} Hub 맥락인데, 검색 경로는 ${[...evidenceBooks].join("·")} stub입니다. ` +
          `억지 연결 없이 ${hub.primary_verse_refs.slice(0, 4).join(" · ")} 앵커로 재질의하세요.`,
      };
    }
  }

  for (const rule of hub.book_chapter_rules ?? []) {
    const chapters = chaptersForBook(rule.book, payload.path, payload.conflict_context);
    if (!chapters.size) continue;
    const blocked = new Set(rule.blocked_chapters ?? []);
    const expected = new Set(rule.expected_chapters ?? []);
    const blockedOnly = blocked.size > 0 && [...chapters].every((c) => blocked.has(c));
    const missesExpected = expected.size > 0 && ![...chapters].some((c) => expected.has(c));
    if (blockedOnly && missesExpected) {
      return {
        code: `${hub.hub_id}_vs_chapter_mismatch`,
        expected_anchor_verses: hub.primary_verse_refs.slice(0, 8),
        hint_ko:
          `질문은 ${rule.book} ${[...(rule.expected_chapters ?? [])].join("/")}장 맥락인데, ` +
          `검색 증거는 ${rule.book} ${[...chapters].join("/")}장입니다. citation lock 앵커로 재질의하세요.`,
      };
    }
  }

  return null;
}

async function detectRegistryHubMismatchAsync(
  query: string,
  payload: Pick<StudioQueryPayload, "path" | "conflict_context" | "preset_id">,
): Promise<QueryTopicMismatch | null> {
  const registry = await loadGolden200AnchorRegistry();
  if (!registry) return null;
  const hub = matchGoldenHubQuery(query, registry);
  if (!hub) return null;
  return detectRegistryHubPathMismatch(query, hub, payload);
}

function detectEveCreationTopic(query: string): boolean {
  const q = norm(query);
  const eveMarkers = ["하와", "갈비", "갈비뼈", "측", "돕는 배필", "돕는 자", "eve", "rib", "tsela"];
  const gen6Markers = ["네피림", "nephilim", "하나님의 아들", "genesis 6", "gen 6"];
  const eve = eveMarkers.some((m) => q.includes(m)) || (q.includes("아담") && (q.includes("뼈") || q.includes("측")));
  const gen6 = gen6Markers.some((m) => q.includes(m));
  return eve && !gen6;
}

function hasPsalm23Evidence(
  payload: Pick<StudioQueryPayload, "path" | "conflict_context">,
): boolean {
  const chapters = chaptersForBook("Ps", payload.path, payload.conflict_context);
  if (chapters.has(23)) return true;
  const parts: string[] = [];
  for (const ref of payload.path?.verse_refs ?? []) parts.push(String(ref));
  return parts.some((ref) => /^Ps\.23/i.test(ref.replace(/\s/g, "")));
}

export function detectQueryTopicMismatch(
  query: string,
  payload: Pick<StudioQueryPayload, "path" | "conflict_context" | "preset_id">,
): QueryTopicMismatch | null {
  const q = query.trim();
  if (!q) return null;

  if (matchGoldenHubTopic(q, "antichrist_666")) {
    const pathBooks = booksFromPath(payload.path);
    const conflictBooks = booksFromConflict(payload.conflict_context);
    const evidenceBooks = new Set([...pathBooks, ...conflictBooks]);
    const wrongPreset = payload.preset_id ? JOB_SUFFERING_PRESET_IDS.has(payload.preset_id) : false;
    const hasApocalyptic = [...evidenceBooks].some((b) => APOCALYPTIC_TOPIC_BOOKS.has(b));
    const stubOnly =
      evidenceBooks.size > 0 &&
      [...evidenceBooks].every((b) => SUFFERING_STUB_BOOKS.has(b) || b === "Heb" || b === "Dan");

    if (
      (wrongPreset && !hasApocalyptic) ||
      (evidenceBooks.size > 0 && !hasApocalyptic && stubOnly)
    ) {
      const anchors = [...hubPrimaryVerseRefs("antichrist_666")];
      return {
        code: "antichrist_666_vs_suffering_stub",
        expected_anchor_verses: anchors,
        hint_ko:
          "질문은 요한계시록 13장(666)·적그리스도 맥락인데, 검색된 경로는 시편·욥기·예레미야 등 고난/신실함 스텁입니다. " +
          "억지 연결 없이 Rev.13.18 · 1John.2.18 citation lock 앵커로 재질의하세요.",
      };
    }
  }

  if (detectPsalm23Topic(q)) {
    const pathBooks = booksFromPath(payload.path);
    const conflictBooks = booksFromConflict(payload.conflict_context);
    const evidenceBooks = new Set([...pathBooks, ...conflictBooks]);
    const hasPs23 = hasPsalm23Evidence(payload);
    const jobHeavy = evidenceBooks.has("Job") && !hasPs23;
    const stubOnly =
      evidenceBooks.size > 0 &&
      !hasPs23 &&
      [...evidenceBooks].every((b) => SUFFERING_STUB_BOOKS.has(b) || b === "Heb" || b === "Dan");

    if (jobHeavy || stubOnly) {
      return {
        code: "psalm_23_vs_suffering_stub",
        expected_anchor_verses: ["Ps.23.1", "Ps.23.4", "Ps.23.6"],
        hint_ko:
          "질문은 시편 23편(목자·신뢰) 맥락인데, 검색된 경로는 욥기·예레미야 등 고난/신실함 스텁입니다. " +
          "억지 연결 없이 Ps.23.1 · Ps.23.4 citation lock 앵커로 재질의하세요.",
      };
    }
  }

  if (detectEveCreationTopic(q)) {
    const gid = payload.conflict_context?.groups?.[0]?.conflict_group_id ?? null;
    const pathBooks = booksFromPath(payload.path);
    const conflictBooks = booksFromConflict(payload.conflict_context);
    const genChapters = new Set<number>();
    for (const book of [...pathBooks, ...conflictBooks]) {
      if (book === "Gen") {
        for (const ref of payload.path?.verse_refs ?? []) {
          const m = /^Gen\.(\d+)/i.exec(ref);
          if (m) genChapters.add(Number(m[1]));
        }
      }
    }
    const wrongGroup = gid != null && GEN6_CONFLICT_IDS.has(gid);
    const gen6Dominated = genChapters.size > 0 && [...genChapters].every((c) => c === 6) && !genChapters.has(2);
    if (wrongGroup || gen6Dominated) {
      return {
        code: "eve_creation_vs_gen6_evidence",
        expected_anchor_verses: ["Gen.2.21", "Gen.2.22", "Gen.2.23", "Gen.2.24"],
        hint_ko:
          "질문은 창세기 2장 하와 창조(갈비·측) 맥락인데, 검색된 충돌면·경로는 창세기 6장 학파 자료입니다. " +
          "Gen.2.21-24 citation lock 앵커로 재질의하세요.",
      };
    }
  }

  return null;
}

export async function detectQueryTopicMismatchAsync(
  query: string,
  payload: Pick<StudioQueryPayload, "path" | "conflict_context" | "preset_id">,
): Promise<QueryTopicMismatch | null> {
  const specific = detectQueryTopicMismatch(query, payload);
  if (specific) return specific;
  return detectRegistryHubMismatchAsync(query, payload);
}

export function buildQueryTopicMismatchAnswerKo(query: string, mismatch: QueryTopicMismatch): string {
  const anchors = mismatch.expected_anchor_verses.join(" · ");
  if (mismatch.code.endsWith("_vs_stub_path") || mismatch.code.endsWith("_vs_blocked_preset")) {
    return [
      `[HYPO] 질문 「${query.trim()}」은 **${mismatch.code.replace(/_vs_.*$/, "")}** Hub short-head 맥락입니다.`,
      "",
      mismatch.hint_ko,
      "",
      `연구 앵커: ${mismatch.expected_anchor_verses.join(" · ")}.`,
      "Citation lock 밖 stub 경로는 LLM·Azure Distill로 연결하지 않습니다.",
    ].join("\n");
  }

  if (mismatch.code.endsWith("_vs_chapter_mismatch")) {
    return [
      `[HYPO] 질문 「${query.trim()}」과 검색된 장(chapter)이 일치하지 않습니다.`,
      "",
      mismatch.hint_ko,
      "",
      `연구 앵커: ${mismatch.expected_anchor_verses.join(" · ")}.`,
    ].join("\n");
  }

  if (mismatch.code === "psalm_23_vs_suffering_stub") {
    return [
      `[HYPO] 질문 「${query.trim()}」은 **시편 23편(목자·신뢰)** 맥락입니다.`,
      "",
      "현재 검색된 경로는 **욥기·예레미야** 등 고난/신실함 스텁이라 질문과 **직접 대응하지 않습니다**. " +
        "Citation lock 밖 stub 경로는 LLM·Azure Distill로 연결하지 않습니다.",
      "",
      `연구 앵커: ${anchors}.`,
      "「시편 23편 목자」 또는 「Ps.23.1-6 학파별 해석」으로 재질의를 권합니다.",
    ].join("\n");
  }

  if (mismatch.code === "antichrist_666_vs_suffering_stub") {
    return [
      `[HYPO] 질문 「${query.trim()}」은 **요한계시록 13장(666)·적그리스도** 맥락입니다.`,
      "",
      "현재 검색된 경로는 **시편·욥기·예레미야** 등 고난/신실함 스텁이라 질문과 **직접 대응하지 않습니다**. " +
        "Citation lock 밖 stub 경로는 LLM·Azure Distill로 연결하지 않습니다.",
      "",
      `연구 앵커: ${anchors}.`,
      "「요한계시록 13장 666」 또는 「적그리스도 요한일서」로 재질의를 권합니다.",
    ].join("\n");
  }

  return [
    `[HYPO] 질문 「${query.trim()}」은 **창세기 2:21-24**(아담의 갈비/측에서 하와 창조) 맥락입니다.`,
    "",
    "현재 검색된 학파 충돌면은 **창세기 6장**(Benei HaElohim·네피림) 자료라 질문과 **직접 대응하지 않습니다**. " +
      "Citation lock 밖 장(chapter) 간 LLM·동적 합성 연결은 하지 않습니다.",
    "",
    `연구 앵커: ${anchors}. 프리셋 \`topic_gen_2_anchor\` 또는 「창세기 2장 하와 창조」로 재질의를 권합니다.`,
  ].join("\n");
}

export async function applyQueryTopicMismatchGuardAsync(
  payload: StudioQueryPayload,
  query: string,
): Promise<StudioQueryPayload> {
  const mismatch = await detectQueryTopicMismatchAsync(query, payload);
  if (!mismatch) return payload;
  return applyQueryTopicMismatchGuard(payload, query, mismatch);
}

export function applyQueryTopicMismatchGuard(
  payload: StudioQueryPayload,
  query: string,
  mismatchOverride?: QueryTopicMismatch | null,
): StudioQueryPayload {
  const mismatch = mismatchOverride ?? detectQueryTopicMismatch(query, payload);
  if (!mismatch) return payload;

  const answer = buildQueryTopicMismatchAnswerKo(query, mismatch);
  return {
    ...payload,
    answer,
    query_mode: `${payload.query_mode || "preset"}+topic_mismatch_guard`,
    synthesis_meta: {
      ok: true,
      schema: "logos_studio_dynamic_synthesis_v1",
      research_only: true,
      send_gate: "HOLD",
      non_gating: true,
      synthesis_mode: "query_topic_mismatch_guard",
      llm_invoked: false,
      answer_ko: answer,
      insight_patch: {
        one_liner_ko: `query-topic guard · ${mismatch.code}`,
        gap_ko: mismatch.hint_ko,
        governance: "[HYPO][NON_GATING]",
      },
      citation_valid: true,
    } as StudioQueryPayload["synthesis_meta"],
    insight_card: {
      preset_id: payload.preset_id,
      slot: payload.insight_card?.slot ?? "topic_mismatch_guard",
      slot_label_ko: payload.insight_card?.slot_label_ko ?? "주제·경로 불일치",
      one_liner_ko: mismatch.hint_ko.slice(0, 120),
      verse_anchors: mismatch.expected_anchor_verses.slice(0, 12),
      gap_ko: mismatch.hint_ko,
      governance: "[HYPO][NON_GATING] · send_gate: HOLD",
    },
  };
}
