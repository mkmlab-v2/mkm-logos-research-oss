import { spawn } from "node:child_process";
import path from "node:path";

import { resolveLogosStudioWorkspaceRoot } from "./logosStudioEmbeddingBridgeV1";
import type { ConflictContextResult } from "./logosStudioConflictBridgeV1";
import type { StudioQueryPayload } from "./logosResearchStudioV1";

export type SynthesisResult =
  | {
      ok: true;
      schema: string;
      research_only: boolean;
      send_gate: string;
      non_gating: boolean;
      synthesis_mode: string;
      llm_invoked: boolean;
      answer_ko: string;
      insight_patch?: {
        one_liner_ko?: string;
        gap_ko?: string;
        governance?: string;
      };
      citation_valid?: boolean;
      citation_check?: Record<string, unknown>;
      allowed_verse_ids?: string[];
    }
  | { ok: false; error: string; reason?: string };

function resolvePythonExecutable(): string {
  return (
    process.env.MKM_PYTHON?.trim() ||
    process.env.LOGOS_STUDIO_SYNTHESIS_PYTHON?.trim() ||
    (process.platform === "win32" ? "py" : "python3")
  );
}

/** Deterministic conflict synthesis on by default when conflict groups exist. */
export function logosStudioDynamicSynthesisEnabled(): boolean {
  const raw = (process.env.LOGOS_STUDIO_DYNAMIC_SYNTHESIS || "auto").trim().toLowerCase();
  if (raw === "0" || raw === "false" || raw === "no" || raw === "off") return false;
  if (raw === "1" || raw === "true" || raw === "yes" || raw === "on") return true;
  return true;
}

export async function synthesizeLogosStudioDynamicAnswer(
  payload: StudioQueryPayload,
  query: string,
): Promise<SynthesisResult> {
  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_missing" };

  const conflict = payload.conflict_context as Extract<ConflictContextResult, { ok: true }> | null | undefined;
  if (!conflict?.group_count) {
    return { ok: false, error: "synthesis_skipped", reason: "no_conflict_context" };
  }

  const py = resolvePythonExecutable();
  const script = path.join(root, "scripts", "synthesize_logos_studio_dynamic_answer_v1.py");
  const preferLlm = (process.env.LOGOS_STUDIO_DYNAMIC_SYNTHESIS_LLM || "").trim().toLowerCase();
  const args = [script, "--stdin-json"];
  if (["1", "true", "yes", "on"].includes(preferLlm)) args.push("--prefer-llm");

  const stdinPayload = JSON.stringify({
    query: query.trim(),
    preset_id: payload.preset_id,
    path: payload.path,
    conflict_context: conflict,
  });

  const timeoutMs = Number(process.env.LOGOS_STUDIO_SYNTHESIS_TIMEOUT_MS || "25000");

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
      try {
        const parsed = JSON.parse(stdout) as SynthesisResult;
        if (!parsed.ok) {
          resolve(parsed);
          return;
        }
        if (code !== 0 && parsed.citation_valid === false) {
          resolve({ ok: false, error: "citation_lint_failed" });
          return;
        }
        resolve(parsed);
      } catch {
        resolve({ ok: false, error: stderr.slice(0, 200) || `exit_${code}` });
      }
    });
    child.stdin.write(stdinPayload);
    child.stdin.end();
  });
}
