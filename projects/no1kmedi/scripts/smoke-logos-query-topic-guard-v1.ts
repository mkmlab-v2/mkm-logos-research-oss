/** Smoke: antichrist/666 topic-path mismatch guard (no Job forced-fit). */
import assert from "node:assert/strict";
import {
  applyQueryTopicMismatchGuard,
  detectAntichrist666Topic,
  detectPsalm23Topic,
  detectQueryTopicMismatch,
} from "../src/lib/logosStudioQueryTopicGuardV1";
import type { StudioQueryPayload } from "../src/lib/logosResearchStudioV1";

const jobStubPayload: StudioQueryPayload = {
  schema: "logos_research_studio_query_v1",
  research_only: true,
  send_gate: "HOLD",
  non_gating: true,
  preset_id: "job_job_suffering_reason",
  query_mode: "preset",
  query: "",
  answer: "stub",
  path: {
    verse_refs: ["Ps.119.86", "Job.2.3", "Jer.4.2"],
    steps: [],
  },
};

const q = "성경에 666 악마의 숫자, 적그리스도에 대해 궁금해";

assert(detectAntichrist666Topic(q), "detectAntichrist666Topic");

const mismatch = detectQueryTopicMismatch(q, jobStubPayload);
assert(mismatch?.code === "antichrist_666_vs_suffering_stub", "mismatch code");

const guarded = applyQueryTopicMismatchGuard(jobStubPayload, q);
assert(
  String(guarded.query_mode).includes("topic_mismatch_guard"),
  "query_mode topic_mismatch_guard",
);
assert(guarded.answer.includes("요한계시록"), "answer mentions revelation");
assert(
  guarded.answer.includes("직접 대응하지 않습니다") ||
    guarded.answer.includes("억지 연결 없이") ||
    guarded.answer.includes("Citation lock 밖 stub"),
  "answer refuses forced-fit",
);

const ps23Q = "시편 23편 — lemma·경로 관점에서 연구 질문을 구체화해 달라";
assert(detectPsalm23Topic(ps23Q), "detectPsalm23Topic");

const ps23StubPayload: StudioQueryPayload = {
  ...jobStubPayload,
  path: {
    verse_refs: ["Job.28.12", "Job.2.3", "Jer.4.2"],
    steps: [],
  },
};
const ps23Mismatch = detectQueryTopicMismatch(ps23Q, ps23StubPayload);
assert(ps23Mismatch?.code === "psalm_23_vs_suffering_stub", "psalm23 mismatch code");

console.log("[smoke-logos-query-topic-guard-v1] passed.");
