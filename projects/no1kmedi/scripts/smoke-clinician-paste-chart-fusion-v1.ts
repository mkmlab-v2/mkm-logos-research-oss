/**
 * Offline smoke: Paste Chart → chat fusion message builder.
 * Run: npx --yes tsx ./scripts/smoke-clinician-paste-chart-fusion-v1.ts
 */

import {
  buildPasteChartFusionAssistantMessage,
  buildPasteChartFusionContext,
} from "../src/lib/clinician-paste-chart-fusion-v1";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const session = {
  patientLabel: "김민수",
  title: "김민수",
  chartSnippet: "요추부 통증",
  summarySnippet: "SOAP A: 소음인 추정",
  adviceTitles: ["주증상", "소음인 망양증 가드레일"],
  assessmentLine: "- 입력 기반 **비임상** 추정 체질 라벨: **소음인**",
  ephemeral: true,
};

const assistant = buildPasteChartFusionAssistantMessage(session);
assert(assistant.includes("SOAP A"), "assistant includes summary");
assert(assistant.includes("조언 카드"), "assistant includes advice titles");
assert(assistant.includes("소음인 망양증"), "assistant includes guardrail title");

const ctx = buildPasteChartFusionContext(session);
assert(ctx.patientLabel === "김민수", "fusion context patient");
assert(ctx.adviceTitles.length === 2, "fusion advice titles");

console.log(
  JSON.stringify(
    {
      schema: "smoke_clinician_paste_chart_fusion_v1",
      ok: true,
      assistant_preview: assistant.split("\n")[0],
      advice_titles: ctx.adviceTitles,
    },
    null,
    2,
  ),
);
