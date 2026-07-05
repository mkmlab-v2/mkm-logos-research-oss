/**
 * Read-only DSSBW canon chunk lookup via monorepo `lookup_dssbw_chunks_v1.py`.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

export type KmCanonCiteChunkV1 = {
  chunk_id: string;
  preview_80chars?: string;
  section_label?: string;
  line_start?: number;
  line_end?: number;
};

export type KmCanonCiteResultV1 =
  | {
      ok: true;
      query: string;
      ranker: string;
      hit_count: number;
      chunks: KmCanonCiteChunkV1[];
    }
  | { ok: false; error: string; method: "python" | "skipped" };

export function resolveMkmWorkspaceRootForCanonCite(): string | null {
  const fromEnv = process.env.MKM_WORKSPACE_ROOT?.trim();
  if (fromEnv && fs.existsSync(path.join(fromEnv, "scripts", "lookup_dssbw_chunks_v1.py"))) {
    return fromEnv;
  }
  const sibling = path.resolve(process.cwd(), "..", "..");
  if (fs.existsSync(path.join(sibling, "scripts", "lookup_dssbw_chunks_v1.py"))) {
    return sibling;
  }
  return null;
}

export function lookupKmCanonCiteChunks(
  query: string,
  opts?: { limit?: number; workspaceRoot?: string },
): KmCanonCiteResultV1 {
  const q = query.trim();
  if (q.length < 2) {
    return { ok: false, error: "query_too_short", method: "skipped" };
  }

  const root = opts?.workspaceRoot?.trim() || resolveMkmWorkspaceRootForCanonCite();
  if (!root) {
    return { ok: false, error: "MKM_WORKSPACE_ROOT not set or lookup script missing", method: "skipped" };
  }

  const scriptPath = path.join(root, "scripts", "lookup_dssbw_chunks_v1.py");
  const limit = Math.min(Math.max(opts?.limit ?? 3, 1), 8);
  const py = process.env.MKM_PYTHON?.trim() || "py";
  const child = spawnSync(
    py,
    [scriptPath, "--query", q, "--limit", String(limit), "--hybrid", "--json"],
    {
      cwd: root,
      encoding: "utf-8",
      maxBuffer: 2 * 1024 * 1024,
      timeout: 15_000,
      windowsHide: true,
    },
  );

  if (child.error) {
    return { ok: false, error: child.error.message, method: "python" };
  }
  if (child.status !== 0) {
    const err = (child.stderr || child.stdout || `exit ${child.status}`).trim();
    return { ok: false, error: err.slice(0, 1500), method: "python" };
  }

  try {
    const parsed = JSON.parse(child.stdout) as {
      query?: string;
      ranker?: string;
      hit_count?: number;
      chunks?: KmCanonCiteChunkV1[];
    };
    const chunks = (parsed.chunks || []).map((row) => ({
      chunk_id: String(row.chunk_id || ""),
      preview_80chars: row.preview_80chars,
      section_label: row.section_label,
      line_start: row.line_start,
      line_end: row.line_end,
    }));
    return {
      ok: true,
      query: parsed.query || q,
      ranker: parsed.ranker || "hybrid_kw_hanja_tfidf_v1",
      hit_count: parsed.hit_count ?? chunks.length,
      chunks,
    };
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return { ok: false, error: `invalid lookup JSON: ${msg}`, method: "python" };
  }
}
