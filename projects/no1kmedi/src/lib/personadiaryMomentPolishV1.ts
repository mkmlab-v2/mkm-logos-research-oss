/**
 * PersonaDiary moment runtime polish — Azure direct via Python bridge.
 * Ollama shallow router / keyword intent classify are separate lanes.
 */
import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";

import type { MomentPolishMeta, MomentResponse } from "./personadiaryMoment";

function resolvePythonExecutable(): string {
  const fromEnv =
    process.env.MKM_PERSONADIARY_MOMENT_PYTHON?.trim() ||
    process.env.MANSERYEOK_PYTHON?.trim();
  if (fromEnv) return fromEnv;
  return process.platform === "win32" ? "py" : "python3";
}

export function runtimeMomentPolishEnabled(): boolean {
  const raw = (process.env.MKM_PERSONADIARY_MOMENT_RUNTIME_POLISH || "auto").trim().toLowerCase();
  if (raw === "0" || raw === "false" || raw === "no" || raw === "off") return false;
  if (raw === "1" || raw === "true" || raw === "yes" || raw === "on") return true;
  // auto: Python probes Azure env in workspace .env
  return true;
}

export async function resolveWorkspaceRoot(): Promise<string | null> {
  const fromEnv = process.env.MKM_WORKSPACE_ROOT?.trim();
  const candidates = [
    fromEnv ? path.resolve(fromEnv) : null,
    path.resolve(process.cwd()),
    path.resolve(process.cwd(), ".."),
    path.resolve(process.cwd(), "..", ".."),
    path.resolve(process.cwd(), "..", "..", ".."),
    path.resolve(process.cwd(), "..", "..", "..", ".."),
  ].filter((c): c is string => Boolean(c));

  for (const root of candidates) {
    try {
      await fs.access(path.join(root, "scripts", "polish_personadiary_moment_runtime_v1.py"));
      return root;
    } catch {
      // continue
    }
  }
  return null;
}

type RuntimePolishResult = {
  summary_ko_polished?: string | null;
  polish_meta?: MomentPolishMeta & { attempts?: MomentPolishMeta[] };
  error?: string;
};

function runRuntimePolishScript(
  root: string,
  stdinJson: string,
): Promise<RuntimePolishResult> {
  const py = resolvePythonExecutable();
  const script = path.join(root, "scripts", "polish_personadiary_moment_runtime_v1.py");
  const timeoutMs = Number(process.env.MKM_PERSONADIARY_MOMENT_RUNTIME_TIMEOUT_MS || "55000");

  return new Promise((resolve) => {
    const child = spawn(py, [script], {
      cwd: root,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
    }, timeoutMs);

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString("utf-8");
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf-8");
    });
    child.on("error", () => {
      clearTimeout(timer);
      resolve({ error: "spawn_failed" });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        resolve({ error: stderr.slice(0, 200) || `exit_${code}` });
        return;
      }
      try {
        resolve(JSON.parse(stdout) as RuntimePolishResult);
      } catch {
        resolve({ error: "invalid_stdout_json" });
      }
    });
    child.stdin.write(stdinJson);
    child.stdin.end();
  });
}

export async function polishMomentRuntime(
  moment: MomentResponse,
  query: string,
): Promise<MomentResponse> {
  if (moment.summary_ko_polished) return moment;
  if (!runtimeMomentPolishEnabled()) return moment;

  const root = await resolveWorkspaceRoot();
  if (!root) return moment;

  const stdin = JSON.stringify({
    summary_ko: moment.summary_ko,
    intent: moment.intent,
    query,
  });

  const parsed = await runRuntimePolishScript(root, stdin);
  const polished = parsed.summary_ko_polished?.trim();
  if (!polished) return moment;

  return {
    ...moment,
    summary_ko_polished: polished,
    polish_meta: {
      lane: "research_only",
      hypothesis_tier: "B",
      applied: true,
      source: "runtime_polish_v1",
      ...(parsed.polish_meta || {}),
    },
  };
}
