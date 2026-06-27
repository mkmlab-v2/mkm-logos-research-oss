import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";

function resolvePythonExecutable(): string {
  return (
    process.env.MKM_PYTHON?.trim() ||
    process.env.LOGOS_STUDIO_EMBEDDING_PYTHON?.trim() ||
    (process.platform === "win32" ? "py" : "python3")
  );
}

export async function resolveLogosStudioWorkspaceRoot(): Promise<string | null> {
  const fromEnv = process.env.MKM_WORKSPACE_ROOT?.trim();
  const marker = path.join("scripts", "encode_logos_studio_query_embedding_v1.py");
  const candidates = [
    fromEnv ? path.resolve(fromEnv) : null,
    path.resolve(process.cwd()),
    path.resolve(process.cwd(), ".."),
    path.resolve(process.cwd(), "..", ".."),
    path.resolve(process.cwd(), "..", "..", ".."),
  ].filter((c): c is string => Boolean(c));

  for (const root of candidates) {
    try {
      await fs.access(path.join(root, marker));
      return root;
    } catch {
      // continue
    }
  }
  return null;
}

export function logosStudioEmbeddingRouterEnabled(): boolean {
  const raw = (process.env.LOGOS_STUDIO_EMBEDDING_ROUTER || "auto").trim().toLowerCase();
  if (raw === "0" || raw === "false" || raw === "no" || raw === "off") return false;
  if (raw === "1" || raw === "true" || raw === "yes" || raw === "on") return true;
  return true;
}

type EncodeResult =
  | { ok: true; vector: number[]; model_id?: string }
  | { ok: false; error: string };

function logosStudioEmbeddingSidecarEnabled(): boolean {
  const raw = (process.env.LOGOS_STUDIO_EMBEDDING_SIDECAR || "auto").trim().toLowerCase();
  if (raw === "0" || raw === "false" || raw === "no" || raw === "off") return false;
  if (raw === "1" || raw === "true" || raw === "yes" || raw === "on") return true;
  return true;
}

function logosStudioEmbeddingSidecarBaseUrl(): string {
  const host = process.env.LOGOS_STUDIO_EMBEDDING_SIDECAR_HOST?.trim() || "127.0.0.1";
  const port = process.env.LOGOS_STUDIO_EMBEDDING_SIDECAR_PORT?.trim() || "18765";
  return `http://${host}:${port}`;
}

async function encodeLogosStudioQueryViaSidecar(query: string): Promise<EncodeResult | null> {
  if (!logosStudioEmbeddingSidecarEnabled()) return null;
  const timeoutMs = Number(process.env.LOGOS_STUDIO_EMBEDDING_SIDECAR_TIMEOUT_MS || "8000");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${logosStudioEmbeddingSidecarBaseUrl()}/encode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
      signal: controller.signal,
    });
    const parsed = (await res.json()) as {
      ok?: boolean;
      vector?: number[];
      error?: string;
      model_id?: string;
    };
    if (!res.ok || !parsed.ok || !Array.isArray(parsed.vector) || parsed.vector.length < 8) {
      return { ok: false, error: parsed.error || `sidecar_http_${res.status}` };
    }
    return { ok: true, vector: parsed.vector, model_id: parsed.model_id };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function encodeLogosStudioQueryViaSubprocess(query: string): Promise<EncodeResult> {
  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return { ok: false, error: "workspace_root_missing" };

  const py = resolvePythonExecutable();
  const script = path.join(root, "scripts", "encode_logos_studio_query_embedding_v1.py");
  const timeoutMs = Number(process.env.LOGOS_STUDIO_EMBEDDING_TIMEOUT_MS || "60000");

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
        resolve({ ok: false, error: stderr.slice(0, 200) || `exit_${code}` });
        return;
      }
      try {
        const parsed = JSON.parse(stdout) as { ok?: boolean; vector?: number[]; error?: string };
        if (!parsed.ok || !Array.isArray(parsed.vector) || parsed.vector.length < 8) {
          resolve({ ok: false, error: parsed.error || "invalid_vector" });
          return;
        }
        resolve({ ok: true, vector: parsed.vector, model_id: (parsed as { model_id?: string }).model_id });
      } catch {
        resolve({ ok: false, error: "invalid_stdout_json" });
      }
    });
    child.stdin.write(query);
    child.stdin.end();
  });
}

export async function encodeLogosStudioQueryEmbedding(query: string): Promise<EncodeResult> {
  const sidecar = await encodeLogosStudioQueryViaSidecar(query);
  if (sidecar?.ok) return sidecar;
  return encodeLogosStudioQueryViaSubprocess(query);
}
