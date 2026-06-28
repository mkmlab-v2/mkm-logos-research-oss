import { spawn } from "node:child_process";
import path from "node:path";

import { resolveLogosStudioWorkspaceRoot } from "./logosStudioEmbeddingBridgeV1";
import type { StudioQueryPayload } from "./logosResearchStudioV1";

export type LemmaBridgeResult =
  | {
      ok: true;
      schema: string;
      research_only: boolean;
      send_gate: string;
      non_gating: boolean;
      synthesis_mode: string;
      llm_invoked: boolean;
      answer_ko: string;
      anchor_verse_refs?: string[];
      neighbor_count?: number;
      neighbors?: Array<{
        verse_ref: string;
        book?: string;
        shared_lemma_count: number;
        lemma_ids?: string[];
        anchor_hits?: string[];
      }>;
      citation_valid?: boolean;
    }
  | { ok: false; error: string; reason?: string };

function resolvePythonExecutable(): string {
  return (
    process.env.MKM_PYTHON?.trim() ||
    process.env.LOGOS_STUDIO_LEMMA_BRIDGE_PYTHON?.trim() ||
    (process.platform === "win32" ? "py" : "python3")
  );
}

export function logosStudioLemmaBridgeEnabled(): boolean {
  const raw = (process.env.LOGOS_STUDIO_LEMMA_BRIDGE || "auto").trim().toLowerCase();
  if (raw === "0" || raw === "false" || raw === "no" || raw === "off") return false;
  if (raw === "1" || raw === "true" || raw === "yes" || raw === "on") return true;
  return true;
}

export async function synthesizeLogosStudioLemmaBridge(
  payload: StudioQueryPayload,
  query: string,
): Promise<LemmaBridgeResult> {
  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_missing" };

  const verseRefs = payload.path?.verse_refs ?? [];
  const nodeIds = payload.path?.node_ids ?? [];
  if (!verseRefs.length && !nodeIds.length) {
    return { ok: false, error: "lemma_bridge_skipped", reason: "no_anchor_verse_refs" };
  }

  const py = resolvePythonExecutable();
  const script = path.join(root, "scripts", "synthesize_logos_studio_lemma_bridge_answer_v1.py");
  const stdinPayload = JSON.stringify({
    query: query.trim(),
    path: payload.path,
    preset_id: payload.preset_id,
  });
  const timeoutMs = Number(process.env.LOGOS_STUDIO_LEMMA_BRIDGE_TIMEOUT_MS || "20000");

  return new Promise((resolve) => {
    const child = spawn(py, [script, "--stdin-json"], {
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
      try {
        const parsed = JSON.parse(stdout) as LemmaBridgeResult;
        if (code !== 0 || !parsed.ok) {
          resolve({
            ok: false,
            error: (parsed as { error?: string }).error || stderr.slice(0, 200) || `exit_${code}`,
            reason: (parsed as { reason?: string }).reason,
          });
          return;
        }
        resolve(parsed);
      } catch {
        resolve({ ok: false, error: stderr.slice(0, 200) || "invalid_stdout_json" });
      }
    });
    child.stdin.write(stdinPayload);
    child.stdin.end();
  });
}
