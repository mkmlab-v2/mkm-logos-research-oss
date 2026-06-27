/**
 * Offline smoke: Explore mesh snapshot builder + hop expand.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  buildCitationDetail,
  buildVerseCitationDetail,
} from "../src/lib/logosResearchCitationDetailV1";
import {
  buildExploreMeshSnapshot,
  expandVisibleFromClick,
  ghostNodeIdForRef,
  hopDistanceMap,
  resolveExplorePositions,
  snapshotPositionsToCache,
} from "../src/lib/logosResearchExploreMeshV1";
import { computeGraphSliceCoverage } from "../src/lib/logosStudioGraphCoverageV1";
import { bfsVisibleNodeIds } from "../src/lib/lensContextMeshBfsV1";
import type { LogosGraphSliceDoc } from "../src/lib/logosResearchGraphTypesV1";
import type { LensContextMeshHopIndexDoc } from "../src/lib/lensContextMeshBfsV1";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(__dirname, "../public/data/logos_studio");

function loadJson<T>(name: string): T {
  return JSON.parse(readFileSync(path.join(DATA, name), "utf8")) as T;
}

function main() {
  const graphDoc = loadJson<LogosGraphSliceDoc>("graph_slice_v1.json");
  const hopIndex = loadJson<LensContextMeshHopIndexDoc>("context_mesh_hop_index_v1.json");
  const seeds = ["job::theme::suffering_reason", "job::verse::job_1_21"];
  const visible = bfsVisibleNodeIds(hopIndex, seeds.filter((id) => hopIndex.nodes[id]), 2, 80);
  assert.ok(visible.size >= 10, `visible_too_small_${visible.size}`);

  const snap = buildExploreMeshSnapshot(graphDoc, visible, {
    pathSpineIds: seeds,
    highlightIds: seeds,
    focusId: seeds[0],
    hopDistances: hopDistanceMap(hopIndex, seeds[0], 6),
  });
  assert.ok(snap, "snapshot_null");
  assert.ok(snap!.ids.length >= 8, `snapshot_nodes_${snap!.ids.length}`);
  assert.ok(snap!.ids.length <= visible.size);
  assert.ok(snap!.positions.length >= snap!.ids.length * 2);
  assert.ok(snap!.links.length >= 2);

  const expanded = expandVisibleFromClick(hopIndex, visible, seeds[0], 120);
  assert.ok(expanded.size >= visible.size, "expand_failed");

  const jobPresetRefs = ["Job.42.10", "Jer.31.4", "Jer.30.7", "Lam.3.22", "Ps.23.3"];
  const coverage = computeGraphSliceCoverage(graphDoc.nodes || [], jobPresetRefs);
  assert.ok(coverage.unmappedRefs.length >= 1, "expected_unmapped_refs_for_ghost");

  const ghostSnap = buildExploreMeshSnapshot(graphDoc, visible, {
    pathSpineIds: seeds,
    ghostRefs: coverage.unmappedRefs,
    activeGhostRef: coverage.unmappedRefs[0],
    ghostAnchorId: seeds[0],
  });
  assert.ok(ghostSnap, "ghost_snapshot_null");
  assert.ok(ghostSnap!.ghostCount >= 1, `ghost_count_${ghostSnap!.ghostCount}`);
  assert.ok(
    ghostSnap!.ids.includes(ghostNodeIdForRef(coverage.unmappedRefs[0])),
    "ghost_id_missing",
  );
  assert.ok(ghostSnap!.links.length >= 2, "ghost_links_missing");

  const cache = snapshotPositionsToCache(snap!);
  const stableId = snap!.ids[0];
  const anchor = cache.get(stableId)!;
  assert.ok(anchor, "anchor_missing_in_cache");
  const expandedSnap = buildExploreMeshSnapshot(graphDoc, expanded, {
    pathSpineIds: seeds,
    focusId: stableId,
    positionCache: cache,
  });
  assert.ok(expandedSnap, "expanded_snapshot_null");
  assert.ok(expandedSnap!.ids.includes(stableId), "stable_id_not_in_expanded");
  const anchorAfter = snapshotPositionsToCache(expandedSnap!).get(stableId)!;
  assert.ok(anchorAfter, "anchor_after_missing");
  assert.ok(
    Math.abs(anchorAfter.x - anchor.x) < 0.01 && Math.abs(anchorAfter.y - anchor.y) < 0.01,
    "position_cache_anchor_drift",
  );

  const placed = resolveExplorePositions(
    (graphDoc.nodes || []).filter((n) => visible.has(n.id)).slice(0, 4),
    cache,
    { focusId: seeds[0], pathSpineIds: seeds },
  );
  assert.ok(placed.size >= 4, "resolve_positions_failed");

  const detail = buildVerseCitationDetail(
    "Job.42.10",
    {
      query: "test",
      answer: "[HYPO] demo",
      path: {
        note_ko: "장기적인 압박 속에서 소망은 인내로 나타납니다.",
        steps: ["node:hope", "Job.42.10"],
        verse_refs: ["Job.42.10", "Ps.23.3"],
        reasoning_path_v1: { path_label_ko: "Job.42.10 → Ps.23.3" },
      },
    },
    Object.fromEntries((graphDoc.nodes || []).map((n) => [n.id, n])),
    {},
  );
  assert.ok(detail.pathNote, "citation_detail_missing_note");

  console.log(
    JSON.stringify({
      ok: true,
      schema: "logos_explore_mesh_offline_smoke_v1",
      visible: visible.size,
      expanded: expanded.size,
      ghostCount: ghostSnap!.ghostCount,
      unmappedRefs: coverage.unmappedRefs.length,
      links: snap!.links.length / 2,
    }),
  );
}

main();
