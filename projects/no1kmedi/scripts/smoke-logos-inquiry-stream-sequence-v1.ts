/**
 * Offline P0-1b hybrid stream sequence — snapshot → s4_delta → s4_done → done.
 * Run: npm run smoke:logos-inquiry-stream
 */
import {
  DEFAULT_FREEZE_LEXICON_META,
  buildLogosInquiryReport,
  evaluateLogosInquiryIntake,
} from "../src/lib/logosInquiryReportV1";
import { iterStreamEvents } from "../src/lib/logosInquiryStreamV1";
import type { StudioQueryPayload } from "../src/lib/logosResearchStudioV1";

const query = "시편 23편 — lemma·경로 관점에서 연구 질문을 구체화해 달라";
const intake = evaluateLogosInquiryIntake(query, "logos", "reports");

const payload = {
  answer:
    "첫 문장은 citation lock 맥락입니다. 둘째 문장은 학파 분기를 요약합니다. 셋째 문장으로 synthesis를 마칩니다.",
  path: {
    verse_refs: ["Ps.23.1", "Ps.23.4"],
    steps: ["root", "lemma"],
    node_ids: ["n1"],
    note_ko: null,
    bridges_matched: null,
  },
  conflict_context: {
    ok: true as const,
    schema: "logos_studio_conflict_context_v1",
    research_only: true,
    send_gate: "HOLD",
    non_gating: true,
    query,
    match_mode: "stub",
    groups: [{ conflict_group_id: "g1", schools: [] }],
    group_count: 1,
  },
  research_only: true,
  non_gating: true,
  send_gate: "HOLD",
  preset_id: "psalm_23_research",
} as StudioQueryPayload;

const report = buildLogosInquiryReport(
  payload,
  query,
  intake,
  DEFAULT_FREEZE_LEXICON_META,
  0,
  null,
);

const events = [...iterStreamEvents(report, 24)];
const names = events.map((e) => e.event);
const snapshot = events.find((e) => e.event === "snapshot");
const done = events.find((e) => e.event === "done");

const ok =
  names[0] === "snapshot" &&
  names[names.length - 1] === "done" &&
  snapshot?.snapshot.S5.signoff_status === "provisional" &&
  snapshot?.snapshot.S5.sections_payload_sha256 === null &&
  events.some((e) => e.event === "s4_delta") &&
  done?.report.sections.S5.signoff_status === "final" &&
  Boolean(done?.report.sections.S5.sections_payload_sha256);

console.log(
  JSON.stringify({
    ok,
    event_sequence: names,
    s4_delta_count: events.filter((e) => e.event === "s4_delta").length,
    final_sha_prefix: done?.report.sections.S5.sections_payload_sha256?.slice(0, 16) ?? null,
  }),
);

if (!ok) process.exit(1);
