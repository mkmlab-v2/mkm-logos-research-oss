/**
 * Smoke: myeongni path mindmap model (exit 0 = pass).
 */
import {
  buildMyeongniPathMindmapModel,
  layoutMyeongniPathMindmapRadial,
} from "../src/lib/myeongniPathMindmapV1";
import { myeongniLiteRecordToMindmapInput } from "../src/lib/myeongniLiteToMindmapInputV1";
import {
  activeNodeIdAtBeat,
  buildMyeongniMindmapDemoTimeline,
} from "../src/lib/myeongniMindmapDemoV1";

const liteFixture = {
  schema: "saju_myeongni_lite_enrich_v1",
  pillars: { year: "庚午", month: "戊寅", day: "甲子", hour: "丙寅" },
  daewoon_current: { pillar: "辛卯", age_start: 36, age_end: 45 },
  sewoon_current: { calendar_year: 2026, pillar: "丙午" },
  ten_god_lite: { counts_combined_ko: { 비견: 2, 정관: 1 } },
  oheng_visible: { dominant_element_visible: "木", weakest_element_visible: "金" },
  strength_hint: { strength_label: "중화 편강" },
};

const mapped = myeongniLiteRecordToMindmapInput("엔진 질의", liteFixture);
if (!mapped?.pillars?.day) {
  console.error("fail: lite mapper");
  process.exit(1);
}

const model = buildMyeongniPathMindmapModel(mapped);

if (model.nodes.length < 8) {
  console.error("fail: expected >= 8 nodes, got", model.nodes.length);
  process.exit(1);
}

const layout = layoutMyeongniPathMindmapRadial(model, 720, 480);
if (layout.length !== model.nodes.length) {
  console.error("fail: layout/node count mismatch");
  process.exit(1);
}

const kinds = new Set(model.nodes.map((n) => n.kind));
for (const need of ["root", "pillar", "luck", "ten_god", "oheng", "strength"]) {
  if (!kinds.has(need)) {
    console.error("fail: missing kind", need);
    process.exit(1);
  }
}

const demoBeats = buildMyeongniMindmapDemoTimeline(model);
if (demoBeats.length < 4 || !activeNodeIdAtBeat(demoBeats, 2000)) {
  console.error("fail: demo timeline");
  process.exit(1);
}

console.log(
  JSON.stringify({
    ok: true,
    nodes: model.nodes.length,
    edges: model.edges.length,
    kinds: [...kinds],
  }),
);
process.exit(0);
