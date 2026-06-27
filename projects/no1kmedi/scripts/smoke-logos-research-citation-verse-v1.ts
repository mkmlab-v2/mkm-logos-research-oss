/**
 * Offline smoke: verse citation detail + shard lookup.
 * npx --yes tsx ./scripts/smoke-logos-research-citation-verse-v1.ts
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { buildVerseCitationDetail } from "../src/lib/logosResearchCitationDetailV1";
import { lookupVerseCitationShard } from "../src/lib/logosResearchVerseCitationShardV1";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const shardPath = path.resolve(__dirname, "../public/data/logos_studio/verse_citation_shard_v1.json");
const shardDoc = JSON.parse(readFileSync(shardPath, "utf8"));

const result = {
  query: "욥 — 고난·의회·scope reset",
  answer: "[HYPO] demo",
  path: {
    note_ko: "장기적인 압박 속에서 소망은 여호와를 인내하며 기다리는 태도를 통해 나타납니다.",
    steps: ["node:hope_prolonged_stress_concept", "node:function_endurance", "Ps.27.14"],
    verse_refs: ["Ps.27.14", "Job.1.6"],
  },
  insight_card: { one_liner_ko: "Job reading pack demo · no causal why-answer", governance: "[HYPO][NON_GATING]" },
};

const psShard = lookupVerseCitationShard("Ps.27.14", shardDoc);
const psDetail = buildVerseCitationDetail("Ps.27.14", result, {}, {}, psShard);
const jobShard = lookupVerseCitationShard("Job.1.6", shardDoc);
const jobDetail = buildVerseCitationDetail("Job.1.6", result, {}, {}, jobShard);

const ok =
  !!psShard?.text_ko &&
  !!psDetail.verseBodyKo &&
  psDetail.verseBodyKo.includes("여호와") &&
  !!jobDetail.verseBodyKo &&
  jobDetail.pathNote !== psDetail.pathNote;

if (!ok) {
  console.error(JSON.stringify({ ok: false, psDetail, jobDetail }));
  process.exit(1);
}

console.log(
  JSON.stringify({
    ok: true,
    schema: "logos_citation_verse_offline_smoke_v1",
    ps_has_body: !!psDetail.verseBodyKo,
    job_has_body: !!jobDetail.verseBodyKo,
    path_note_differs: jobDetail.pathNote !== psDetail.pathNote,
  }),
);
