import { spawn } from "node:child_process";
import path from "node:path";

import { resolveLogosStudioWorkspaceRoot } from "./logosStudioEmbeddingBridgeV1";
import { mergeLogosStudioWorkspaceEnv } from "./logosStudioWorkspaceEnvV1";
import type { StudioQueryPayload } from "./logosResearchStudioV1";
import { settleChildOrTimeout } from "./logosStudioSpawnSettleV1";

export type Gen2AzureDistillResult =
  | {
      ok: true;
      schema: string;
      research_only: boolean;
      send_gate: string;
      non_gating: boolean;
      synthesis_mode: string;
      distill_backend: string;
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
      evidence_count?: number;
      latency_ms?: number;
    }
  | { ok: false; error: string; azure_error?: string; citation_valid?: boolean };

export const GEN2_EVE_PRESET_ID = "topic_gen_2_anchor";

export type AzureDistillResult = Gen2AzureDistillResult;

function resolvePythonExecutable(): string {
  return (
    process.env.MKM_PYTHON?.trim() ||
    process.env.LOGOS_STUDIO_AZURE_PYTHON?.trim() ||
    process.env.LOGOS_STUDIO_GEN2_AZURE_PYTHON?.trim() ||
    (process.platform === "win32" ? "py" : "python3")
  );
}

/** Preset-agnostic Azure T3 distill — auto when Azure env present unless explicitly off. */
export function logosStudioAzureDistillEnabled(): boolean {
  const raw = (
    process.env.LOGOS_STUDIO_AZURE_DISTILL ||
    process.env.LOGOS_STUDIO_GEN2_AZURE_DISTILL ||
    "auto"
  )
    .trim()
    .toLowerCase();
  if (raw === "0" || raw === "false" || raw === "no" || raw === "off") return false;
  if (raw === "1" || raw === "true" || raw === "yes" || raw === "on") return true;
  return true;
}

/** @deprecated use logosStudioAzureDistillEnabled */
export function logosStudioGen2AzureDistillEnabled(): boolean {
  return logosStudioAzureDistillEnabled();
}

export async function synthesizeLogosStudioAzureDistill(
  payload: StudioQueryPayload,
  query: string,
  opts?: { depthMode?: "essay" | "scholar"; askFace?: "believer" | "research" },
): Promise<AzureDistillResult> {
  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_missing" };

  const py = resolvePythonExecutable();
  const script = path.join(root, "scripts", "synthesize_logos_studio_azure_distill_v1.py");
  const stdinPayload = JSON.stringify({
    query: query.trim(),
    preset_id: payload.preset_id,
    path: payload.path,
    conflict_context: payload.conflict_context ?? null,
    depth_mode: opts?.depthMode === "scholar" ? "scholar" : "essay",
    ask_face: opts?.askFace === "research" ? "research" : "believer",
  });

  const timeoutMs = Number(
    process.env.LOGOS_STUDIO_AZURE_TIMEOUT_MS ||
      process.env.LOGOS_STUDIO_GEN2_AZURE_TIMEOUT_MS ||
      "130000",
  );

  return new Promise((resolve) => {
    const child = spawn(py, [script, "--stdin-json"], {
      cwd: root,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...mergeLogosStudioWorkspaceEnv(process.env),
        LOGOS_STUDIO_DISTILL_BACKEND: "azure",
        MKM_LOGOS_LLM_DISTILL_ENABLE: process.env.MKM_LOGOS_LLM_DISTILL_ENABLE || "1",
      },
    });
    let stdout = "";
    let stderr = "";
    const { settle } = settleChildOrTimeout(child, timeoutMs, resolve, {
      ok: false,
      error: "timeout",
    });

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf-8");
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf-8");
    });
    child.on("error", () => {
      settle({ ok: false, error: "spawn_failed" });
    });
    child.on("close", (code) => {
      try {
        const parsed = JSON.parse(stdout) as AzureDistillResult;
        if (!parsed.ok) {
          settle(parsed);
          return;
        }
        if (code !== 0 && parsed.citation_valid === false) {
          settle({ ok: false, error: "citation_lint_failed" });
          return;
        }
        settle(parsed);
      } catch {
        settle({ ok: false, error: stderr.slice(0, 200) || `exit_${code}` });
      }
    });
    child.stdin.write(stdinPayload);
    child.stdin.end();
  });
}

/** @deprecated use synthesizeLogosStudioAzureDistill */
export async function synthesizeLogosStudioGen2AzureDistill(
  payload: StudioQueryPayload,
  query: string,
): Promise<Gen2AzureDistillResult> {
  return synthesizeLogosStudioAzureDistill(payload, query);
}
