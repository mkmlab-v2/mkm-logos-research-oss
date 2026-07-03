/**
 * Offline Ask graph sidecar seed + pulse + trust tooltip contract smoke (no HTTP).
 *
 * Run from projects/no1kmedi:
 *   npm run smoke:logos-ask-graph-sidecar
 */

import goldenRegistry from "../public/data/logos_studio/golden_200_anchor_registry_v1.json";
import {
  buildAskGraphNodeTooltips,
  collectAskGraphSeedRefs,
  exceedsAskGraphRenderBudget,
  filterPathMindmapForVizMode,
  resolveAskGraphSeedIds,
  shouldPulseAskGraph,
} from "../src/lib/logosAskGraphSidecarV1";
import {
  buildPublicCitationLockModel,
  citationLockVerseTitle,
  extractGoldenHubIdFromQueryMode,
} from "../src/lib/logosInquiryAskDisplayV1";
import { buildPathMindmapModel } from "../src/lib/logosResearchPathMindmapV1";
import {
  applyInquiryS4QualityGate,
  stripPublicResearchTagsForS4,
} from "../src/lib/logosInquiryReportV1";

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(message);
}

const GAP12_HUB_IDS = [
  "isaiah53_suffering_servant",
  "good_samaritan_parable",
  "prodigal_son_parable",
  "corinthians13_love",
  "galatians5_fruit",
  "philippians2_kenosis",
  "james2_faith_works",
  "1pet_suffering_imitation",
  "ruth_loyalty_covenant",
  "samuel_david_anointing",
  "elijah_carmel",
  "micah6_justice",
] as const;

const seeds = collectAskGraphSeedRefs(
  ["Job.42.10", "Ps.23.3"],
  ["Job.42.10", "Gematria_Pin:abc123", "Rom.8.28"],
);
assert(seeds.length === 3, `seed_count_${seeds.length}`);
assert(!seeds.some((s) => /Gematria_Pin/i.test(s)), "forbidden_pin_filtered");

const graphDoc = {
  nodes: [
    { id: "v:job42", ref: "Job.42.10", label: "Job.42.10", kind: "verse" },
    { id: "v:ps23", ref: "Ps.23.3", label: "Ps.23.3", kind: "verse" },
    { id: "v:rom8", ref: "Rom.8.28", label: "Rom.8.28", kind: "verse" },
    { id: "v:isa53", ref: "Isa.53.5", label: "Isa.53.5", kind: "verse" },
    { id: "v:luke10", ref: "Luke.10.33", label: "Luke.10.33", kind: "verse" },
  ],
  edges: [],
};

const ids = resolveAskGraphSeedIds(seeds, graphDoc);
assert(ids.length === 3, `resolved_ids_${ids.length}`);

assert(shouldPulseAskGraph("snapshot"), "pulse_snapshot");
assert(shouldPulseAskGraph("done"), "pulse_done");
assert(!shouldPulseAskGraph("idle"), "no_pulse_idle");

const model = buildPathMindmapModel({
  query: "욥 고난",
  verseRefs: ["Job.42.10", "Ps.23.3"],
});
const tips = buildAskGraphNodeTooltips(model, ["Job.42.10"], ["Job.42.10"]);
const verseTip = Object.values(tips).find((t) => t.includes("Job.42.10"));
assert(Boolean(verseTip?.includes("고정")), "verse_tooltip_public");
assert(!Object.values(tips).some((t) => /repair_v2/i.test(t)), "no_repair_v2_tooltip");

const pathOnly = filterPathMindmapForVizMode(
  {
    ...model,
    nodes: [...model.nodes, { id: "m1", label: "mesh", kind: "mesh", depth: 2 }],
    edges: [...model.edges, { from: model.rootId, to: "m1" }],
  },
  "path",
);
assert(!pathOnly.nodes.some((n) => n.kind === "mesh"), "path_mode_strips_mesh");

assert(citationLockVerseTitle("Ps.23.1").includes("고정 구절"), "citation_title");
assert(exceedsAskGraphRenderBudget(49), "budget_over");
assert(!exceedsAskGraphRenderBudget(40), "budget_ok");

assert(
  extractGoldenHubIdFromQueryMode(
    "preset+graphrag_custom+inquiry_golden_hub_isaiah53_suffering_servant+reading_pack",
  ) === "isaiah53_suffering_servant",
  "hub_id_from_query_mode",
);

const citationModel = buildPublicCitationLockModel({
  preset_id: "topic_isa_anchor",
  query_mode: "preset+inquiry_golden_hub_isaiah53_suffering_servant+reading_pack",
  sections: {
    S1: {
      section_id: "S1_citation_lock",
      title_ko: "Citation Lock",
      verse_refs: ["Isa.53.5", "Isa.53.7"],
      citation_lock_anchors: ["Isa.53.5", "Isa.53.7", "1Pet.2.24"],
      security_note_ko: "test",
    },
    S2: {
      section_id: "S2_lexicon_hash",
      title_ko: "Lexicon",
      lemma_edge_line_count: 1,
      min_line_count_floor: 1,
      floor_pass: true,
      freeze_manifest_pointer: "x",
      manifest_sha256: "y",
    },
    S3: { section_id: "S3_divergence", title_ko: "Divergence", groups: [], note_ko: "n" },
    S4: { section_id: "S4_insight", title_ko: "Insight", body_ko: "body", bullets_ko: [] },
    S5: { section_id: "S5_governance", title_ko: "Gov", send_gate: "HOLD", research_only: true },
  },
});
assert(citationModel?.hubId === "isaiah53_suffering_servant", "citation_model_hub_id");
assert(citationModel?.pathLabel === "hub_preset", "citation_model_hub_path");

let gap12Checked = 0;
for (const hubId of GAP12_HUB_IDS) {
  const entry = goldenRegistry.entries.find((e) => e.hub_id === hubId);
  assert(Boolean(entry), `gap12_registry_${hubId}`);
  const refs = entry?.primary_verse_refs ?? [];
  const hubSeeds = collectAskGraphSeedRefs(refs, refs);
  assert(hubSeeds.length >= 2, `gap12_seeds_${hubId}_${hubSeeds.length}`);
  gap12Checked += 1;
}
assert(gap12Checked === GAP12_HUB_IDS.length, `gap12_count_${gap12Checked}`);

const stripped = stripPublicResearchTagsForS4(
  "### 반증·대안\n억지 연결하지 않습니다 [NON_GATING].\n\n[NON_GATING]",
);
assert(!/\[NON_GATING\]/i.test(stripped), "s4_public_tags_stripped");

const gated = applyInquiryS4QualityGate({
  body: "LLM·Azure Distill로 억지 연결하지 않습니다 [NON_GATING]. Gen.1.26.",
  bullets: ["하나님 형상은 인간 존엄의 근거입니다.", "", "", ""],
  verseRefs: ["Gen.1.26", "Gen.1.27"],
});
assert(!/\[NON_GATING\]|\bresearch_only\b/i.test(gated.body), "quality_gate_public_body_clean");
assert(gated.body.includes("### 핵심 주장"), "quality_gate_five_sections");

console.log(
  JSON.stringify({
    ok: true,
    seeds,
    resolved_ids: ids,
    tooltip_sample: verseTip,
    path_nodes: pathOnly.nodes.length,
    gap12_hubs: gap12Checked,
    citation_hub_id: citationModel?.hubId,
  }),
);
