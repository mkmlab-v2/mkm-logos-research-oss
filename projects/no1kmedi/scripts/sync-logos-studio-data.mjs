#!/usr/bin/env node
/** Copy Logos Graph Studio SSOT JSON into public/data for on-domain API. */
import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pkgRoot = path.resolve(__dirname, "..");
const workspaceRoot = path.resolve(pkgRoot, "..", "..");
const artifactDir = path.join(workspaceRoot, "docs", "final", "artifacts");
const outDir = path.join(pkgRoot, "public", "data", "logos_studio");

/** When artifact mirror is gitignored/missing on VPS, copy from rehearsal SSOT. */
const ARTIFACT_FALLBACK = {
  "showroom_logos_job_reading_pack_slice_v1_latest.json": path.join(
    workspaceRoot,
    "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_job_reading_pack_slice_v1.json",
  ),
};

const PAIRS = [
  ["showroom_meaning_topology_qa_presets_v1_latest.json", "qa_presets_v1.json"],
  ["showroom_meaning_topology_qa_router_sidecar_v1_latest.json", "qa_router_sidecar_v1.json"],
    ["logos_studio_graph_slice_ui_lite_v1_latest.json", "graph_slice_v1.json"],
  ["showroom_meaning_topology_graph_slice_v1_latest.json", "graph_slice_full_v1.json"],
  ["lens_context_mesh_hop_index_logos_ui_lite_v1_latest.json", "context_mesh_hop_index_v1.json"],
  ["showroom_era_insight_lattice_genesis_v1_latest.json", "era_insight_lattice_genesis_v1.json"],
  ["logos_studio_preset_taxonomy_v1_latest.json", "preset_taxonomy_v1.json"],
  ["logos_cross_ref_sample_shard_v1_latest.json", "cross_ref_sample_shard_v1.json"],
  ["bigset_studio_conflict_sidecar_v1_latest.json", "bigset_conflict_sidecar_v1.json"],
  ["showroom_logos_job_reading_pack_slice_v1_latest.json", "job_reading_pack_slice_v1.json"],
  [
    "showroom_logos_isaiah_youtube_reading_pack_slice_v1_latest.json",
    "isaiah_youtube_reading_pack_slice_v1.json",
  ],
  ["logos_studio_semantic_router_lexical_index_v1_latest.json", "semantic_router_lexical_index_v1.json"],
  ["logos_studio_semantic_router_embedding_index_v1_latest.json", "semantic_router_embedding_index_v1.json"],
  ["logos_studio_verse_citation_shard_v1_latest.json", "verse_citation_shard_v1.json"],
  ["logos_studio_a4_synthesis_bundle_v1_latest.json", "a4_synthesis_bundle_v1.json"],
  ["logos_studio_31k_bloom_secondary_fetch_v1_latest.json", "bloom_31k_index_v1.json"],
  ["logos_studio_dynamic_subgraph_router_v1_latest.json", "dynamic_subgraph_router_v1.json"],
  ["logos_krv_versification_sidecar_v1_latest.json", "krv_versification_sidecar_v1.json"],
];

function runEmbedRouterSidecarMerge() {
  const mergePy = path.join(workspaceRoot, "scripts", "merge_logos_studio_embed_router_sidecar_v1.py");
  const pyCandidates =
    process.platform === "win32"
      ? [process.env.PYTHON || "py", "python"]
      : [process.env.PYTHON || "python3", "python", "py"];
  let res = null;
  for (const py of pyCandidates) {
    res = spawnSync(py, [mergePy], {
      cwd: workspaceRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (res.error?.code === "ENOENT") continue;
    break;
  }
  if (!res || res.status !== 0) {
    console.warn(
      `[sync-logos-studio-data] embed router merge skipped exit=${res?.status ?? "missing"}`,
      res?.stderr?.trim() || res?.stdout?.trim(),
    );
    return;
  }
  console.log("[sync-logos-studio-data] embed_router_sidecar_merge ok");
}

function runRouterVerseStubPatch() {
  const patchPy = path.join(workspaceRoot, "scripts", "patch_logos_studio_graph_slice_router_verse_stubs_v1.py");
  const pyCandidates =
    process.platform === "win32"
      ? [process.env.PYTHON || "py", "python"]
      : [process.env.PYTHON || "python3", "python", "py"];
  let res = null;
  for (const py of pyCandidates) {
    res = spawnSync(py, [patchPy], {
      cwd: workspaceRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (res.error?.code === "ENOENT") continue;
    break;
  }
  if (!res) return;
  if (res.status !== 0) {
    console.warn(
      `[sync-logos-studio-data] router verse stub patch skipped exit=${res.status}`,
      res.stderr?.trim() || res.stdout?.trim(),
    );
    return;
  }
  try {
    const doc = JSON.parse(String(res.stdout || "").trim().split("\n").pop() || "{}");
    if (doc.added_count) {
      console.log(`[sync-logos-studio-data] router_verse_stub_patch added=${doc.added_count}`);
    }
  } catch {
    console.log("[sync-logos-studio-data] router_verse_stub_patch ok");
  }
}

function runUiLiteGraphSlice() {
  const litePy = path.join(workspaceRoot, "scripts", "build_logos_studio_graph_slice_ui_lite_v1.py");
  const pyCandidates =
    process.platform === "win32"
      ? [process.env.PYTHON || "py", "python"]
      : [process.env.PYTHON || "python3", "python", "py"];
  let res = null;
  for (const py of pyCandidates) {
    res = spawnSync(py, [litePy, "--max-nodes", "900"], {
      cwd: workspaceRoot,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (res.error?.code === "ENOENT") continue;
    break;
  }
  if (!res || res.status !== 0) {
    console.warn(
      `[sync-logos-studio-data] ui lite graph build skipped exit=${res?.status ?? "missing"}`,
      res?.stderr?.trim() || res?.stdout?.trim(),
    );
    return;
  }
  console.log("[sync-logos-studio-data] ui_lite_graph_slice ok");
}

try {
  runEmbedRouterSidecarMerge();
  runRouterVerseStubPatch();
  runUiLiteGraphSlice();
  await mkdir(outDir, { recursive: true });
  let copied = 0;
  let skipped = 0;
  for (const [srcName, destName] of PAIRS) {
    let src = path.join(artifactDir, srcName);
    const dest = path.join(outDir, destName);
    try {
      await copyFile(src, dest);
      console.log(`[sync-logos-studio-data] ${destName}`);
      copied += 1;
    } catch (error) {
      if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
        const fallback = ARTIFACT_FALLBACK[srcName];
        if (fallback) {
          try {
            await copyFile(fallback, dest);
            console.log(`[sync-logos-studio-data] ${destName} (fallback)`);
            copied += 1;
            continue;
          } catch {
            /* fall through to skip */
          }
        }
        console.warn(`[sync-logos-studio-data] skip missing ${srcName} (keep existing ${destName})`);
        skipped += 1;
        continue;
      }
      throw error;
    }
  }
  if (copied === 0 && skipped > 0) {
    console.warn("[sync-logos-studio-data] no artifacts copied; using packaged public/data if present");
  }
} catch (error) {
  console.error("[sync-logos-studio-data] failed.");
  if (error instanceof Error) console.error(error.message);
  process.exitCode = 1;
}
