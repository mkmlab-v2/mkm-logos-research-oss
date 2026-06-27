import { spawn } from "node:child_process";
import path from "node:path";

import { resolveLogosStudioWorkspaceRoot } from "./logosStudioEmbeddingBridgeV1";

export type ConflictSchoolRow = {
  school_tier?: string;
  interpretation_ko?: string;
  citation_lock_anchors?: string[];
  verse_refs?: string[];
  traditions?: string[];
  labels?: string[];
};

export type ConflictGroupRow = {
  conflict_group_id?: string;
  lexicon_base?: string;
  school_count?: number;
  schools?: ConflictSchoolRow[];
  retrieval_score?: number;
};

export type ConflictContextResult =
  | {
      ok: true;
      schema: string;
      research_only: boolean;
      send_gate: string;
      non_gating: boolean;
      query: string;
      preset_id?: string | null;
      preset_conflict_group_id?: string | null;
      match_mode: string;
      group_count: number;
      groups: ConflictGroupRow[];
      ui_contract?: { panel_title_ko?: string; disclaimer_ko?: string };
    }
  | { ok: false; error: string };

function resolvePythonExecutable(): string {
  return (
    process.env.MKM_PYTHON?.trim() ||
    process.env.LOGOS_STUDIO_CONFLICT_PYTHON?.trim() ||
    (process.platform === "win32" ? "py" : "python3")
  );
}

export function logosStudioConflictRetrievalEnabled(): boolean {
  const raw = (process.env.LOGOS_STUDIO_CONFLICT_RETRIEVAL || "auto").trim().toLowerCase();
  if (raw === "0" || raw === "false" || raw === "no" || raw === "off") return false;
  if (raw === "1" || raw === "true" || raw === "yes" || raw === "on") return true;
  return true;
}

export async function retrieveLogosStudioConflictContext(
  query: string,
  presetId?: string | null,
): Promise<ConflictContextResult> {
  const q = query.trim();
  if (!q) return { ok: false, error: "empty_query" };

  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_missing" };

  const py = resolvePythonExecutable();
  const script = path.join(root, "scripts", "retrieve_logos_studio_conflict_context_v1.py");
  const args = [script, "--query-stdin"];
  if (presetId) args.push("--preset-id", presetId);
  const timeoutMs = Number(process.env.LOGOS_STUDIO_CONFLICT_TIMEOUT_MS || "20000");

  return new Promise((resolve) => {
    const child = spawn(py, args, {
      cwd: root,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => child.kill("SIGTERM"), timeoutMs);

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf-8");
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf-8");
    });
    child.on("error", () => {
      clearTimeout(timer);
      resolve({ ok: false, error: "spawn_failed" });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        try {
          const parsed = JSON.parse(stdout) as { error?: string };
          resolve({ ok: false, error: parsed.error || stderr.slice(0, 200) || `exit_${code}` });
        } catch {
          resolve({ ok: false, error: stderr.slice(0, 200) || `exit_${code}` });
        }
        return;
      }
      try {
        const parsed = JSON.parse(stdout) as ConflictContextResult;
        if (!parsed.ok || !Array.isArray((parsed as { groups?: unknown }).groups)) {
          resolve({ ok: false, error: (parsed as { error?: string }).error || "invalid_conflict" });
          return;
        }
        resolve(parsed);
      } catch {
        resolve({ ok: false, error: "invalid_stdout_json" });
      }
    });
    child.stdin.write(q);
    child.stdin.end();
  });
}
