import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";

import type { LogosRouterPathV1 } from "./logosResearchHighlightV1";
import { resolveLogosStudioWorkspaceRoot } from "./logosStudioEmbeddingBridgeV1";

export type GraphragEncodeResult =
  | {
      ok: true;
      query: string;
      router_path_v1: LogosRouterPathV1;
      bridges_matched: number;
      paths_count: number;
      highlight_node_ids: string[];
      answer_ko: string;
      paths_preview?: Array<{ path_id?: string; note_ko?: string; steps?: string[] }>;
    }
  | { ok: false; error: string; bridges_matched?: number };

function resolvePythonExecutable(): string {
  return (
    process.env.MKM_PYTHON?.trim() ||
    process.env.LOGOS_STUDIO_GRAPHRAG_PYTHON?.trim() ||
    (process.platform === "win32" ? "py" : "python3")
  );
}

export function logosStudioGraphragRouterEnabled(): boolean {
  const raw = (process.env.LOGOS_STUDIO_GRAPHRAG_ROUTER || "auto").trim().toLowerCase();
  if (raw === "0" || raw === "false" || raw === "no" || raw === "off") return false;
  if (raw === "1" || raw === "true" || raw === "yes" || raw === "on") return true;
  return true;
}

export async function encodeLogosStudioQueryGraphrag(query: string): Promise<GraphragEncodeResult> {
  const q = query.trim();
  if (!q) return { ok: false, error: "empty_query" };

  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_missing" };

  const py = resolvePythonExecutable();
  const script = path.join(root, "scripts", "encode_logos_studio_query_graphrag_v1.py");
  const timeoutMs = Number(process.env.LOGOS_STUDIO_GRAPHRAG_TIMEOUT_MS || "25000");

  return new Promise((resolve) => {
    const child = spawn(py, [script, "--query-stdin"], {
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
          const parsed = JSON.parse(stdout) as { error?: string; bridges_matched?: number };
          resolve({
            ok: false,
            error: parsed.error || stderr.slice(0, 200) || `exit_${code}`,
            bridges_matched: parsed.bridges_matched,
          });
        } catch {
          resolve({ ok: false, error: stderr.slice(0, 200) || `exit_${code}` });
        }
        return;
      }
      try {
        const parsed = JSON.parse(stdout) as GraphragEncodeResult;
        if (!parsed.ok || !parsed.router_path_v1) {
          resolve({ ok: false, error: (parsed as { error?: string }).error || "invalid_graphrag" });
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

/** Best-effort check that graphrag script exists (dev diagnostics). */
export async function graphragScriptPresent(): Promise<boolean> {
  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return false;
  try {
    await fs.access(path.join(root, "scripts", "encode_logos_studio_query_graphrag_v1.py"));
    return true;
  } catch {
    return false;
  }
}
