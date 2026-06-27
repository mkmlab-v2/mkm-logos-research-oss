/**
 * Offline path mindmap model + layout smoke (no HTTP).
 *
 * Run from projects/no1kmedi:
 *   npm run smoke:logos-path-mindmap
 */

import {
  buildPathMindmapModel,
  curvedEdgePath,
  layoutPathMindmapRadial,
  mindmapNodeIdsForVerseRef,
} from "../src/lib/logosResearchPathMindmapV1";
import { buildMindmapMeshSummary } from "../src/lib/logosResearchPathMindmapMeshV1";
import { PRESET_SPINE_ANGLE_DEG_V1 } from "../src/lib/pathMindmapCoreV1";

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

const model = buildPathMindmapModel({
  query: "욥 — 고난·의회",
  pathSteps: ["field:job", "lens:logos", "gap:why_suffer"],
  verseRefs: ["Job.42.10", "Ps.23.3", "Ps.27.14"],
  spineItems: [
    { id: "spine:1", label: "Field" },
    { id: "spine:2", label: "Lens" },
    { id: "spine:3", label: "Gap" },
  ],
});

assert(model.rootId === "mm:root", "root_id");
assert(model.nodes.length >= 7, `node_count_${model.nodes.length}`);
assert(model.edges.length >= 6, `edge_count_${model.edges.length}`);
assert(model.nodes.some((n) => n.kind === "verse"), "verse_nodes");
assert(model.nodes.some((n) => n.kind === "spine"), "spine_nodes");

const layout = layoutPathMindmapRadial(model, 720, 480, {
  presetId: "job_job_suffering_reason",
  leafKinds: ["verse"],
});
assert(layout.length === model.nodes.length, "layout_len");
const root = layout.find((n) => n.id === model.rootId);
assert(Boolean(root && root.x > 0 && root.y > 0), "root_position");

const layoutGeneric = layoutPathMindmapRadial(model, 720, 480, { leafKinds: ["verse"] });
const spinePresetNodes = layout.filter((n) => n.kind === "spine");
const spineGenericNodes = layoutGeneric.filter((n) => n.kind === "spine");
assert(
  PRESET_SPINE_ANGLE_DEG_V1.job_job_suffering_reason?.length >= 3,
  "job_preset_angles",
);
assert(spinePresetNodes.length >= 2 && spineGenericNodes.length >= 2, "spine_pair");
const s1 = spinePresetNodes[1];
const g1 = spineGenericNodes[1];
assert(
  Math.abs(s1.x - g1.x) > 1 || Math.abs(s1.y - g1.y) > 1,
  "preset_layout_differs",
);

const meshMerged = buildMindmapMeshSummary({
  base: model,
  graphDoc: {
    nodes: [
      { id: "n1", label: "theme-a", kind: "theme" },
      { id: "n2", label: "theme-b", kind: "theme" },
      { id: "spine:1", label: "Field" },
    ],
    edges: [
      { src: "spine:1", dst: "n1" },
      { src: "n1", dst: "n2" },
    ],
  },
  hopIndex: {
    schema_version: "v1",
    nodes: {
      "spine:1": { neighbors: [{ id: "n1" }] },
      n1: { neighbors: [{ id: "spine:1" }, { id: "n2" }] },
      n2: { neighbors: [{ id: "n1" }] },
    },
  },
  seedIds: ["spine:1"],
  nodeById: {
    "spine:1": { id: "spine:1", label: "Field" },
    n1: { id: "n1", label: "theme-a" },
    n2: { id: "n2", label: "theme-b" },
  },
  maxMesh: 10,
});
assert(meshMerged.meshShown >= 1, `mesh_shown_${meshMerged.meshShown}`);
assert(meshMerged.model.nodes.some((n) => n.kind === "mesh"), "mesh_nodes");

const verseHits = mindmapNodeIdsForVerseRef("Job.42.10", model);
assert(verseHits.length === 1, "verse_ref_lookup");

const path = curvedEdgePath(100, 100, 200, 150);
assert(path.startsWith("M ") && path.includes(" Q "), "curved_edge_path");

console.log(
  JSON.stringify({
    ok: true,
    nodes: model.nodes.length,
    edges: model.edges.length,
    mesh_shown: meshMerged.meshShown,
    layout_root: root ? { x: root.x, y: root.y } : null,
  }),
);
