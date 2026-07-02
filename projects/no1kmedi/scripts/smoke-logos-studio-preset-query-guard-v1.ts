/**
 * Offline smoke: preset–query guard alignment + auto-route.
 * Run: npx --yes tsx ./scripts/smoke-logos-studio-preset-query-guard-v1.ts
 */

import {
  applyPresetQueryGuard,
  queryAlignsWithPreset,
  scoreQueryPresetAlignment,
} from "../src/lib/logosStudioPresetQueryGuardV1";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const jobPreset = {
  id: "job_job_suffering_reason",
  prompt_ko: "욥기 — 고난과 의회, 왜 고난인가?",
  keywords: ["욥", "고난", "job", "suffering"],
};

const nephPreset = {
  id: "bigset_topic_nephilim",
  prompt_ko: "네피림(Nephilim)과 거인 전통은 어떻게 해석되나?",
  keywords: ["네피림", "nephilim", "감시자", "거인"],
};

assert(scoreQueryPresetAlignment(nephPreset, "네피림") >= 2, "nephilim keyword score");
assert(!queryAlignsWithPreset(jobPreset, "네피림"), "job preset misaligned with nephilim");
assert(queryAlignsWithPreset(jobPreset, "욥기 고난 why"), "job preset aligned");

const auto = applyPresetQueryGuard({
  presets: [jobPreset, nephPreset],
  requestedPresetId: "job_job_suffering_reason",
  query: "네피림",
  queryRoutedPresetId: "bigset_topic_nephilim",
  queryMatch: "text",
});
assert(auto.preset_id === "bigset_topic_nephilim", "auto route to nephilim");
assert(auto.preset_guard?.action === "auto_route", "auto_route action");
assert((auto.preset_guard?.message_ko?.includes("자동 전환")) === true, "guard message");

const keep = applyPresetQueryGuard({
  presets: [jobPreset, nephPreset],
  requestedPresetId: "job_job_suffering_reason",
  query: "욥기 고난",
  queryRoutedPresetId: "bigset_topic_nephilim",
  queryMatch: "text",
});
assert(keep.preset_id === "job_job_suffering_reason", "keep job when aligned");

console.log(
  JSON.stringify(
    {
      schema: "smoke_logos_studio_preset_query_guard_v1",
      ok: true,
      auto_route: auto.preset_id,
      keep_job: keep.preset_id,
    },
    null,
    2,
  ),
);
