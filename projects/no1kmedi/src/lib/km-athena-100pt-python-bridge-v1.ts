import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { resolveMkmWorkspaceRoot } from "./km-workspace-root-v1";

export type Athena100ptChainRequest = {
  slug: string;
  validateSchema?: boolean;
  updatePointer?: boolean;
  writeLatest?: boolean;
};

export type Athena100ptChainResult =
  | {
      ok: true;
      slug: string;
      hanTurnJson: string;
      hanTurnMd: string;
      reportJson: string;
      reportMd: string;
      reportMdContent: string;
    }
  | { ok: false; error: string; stderr?: string };

function parseStdoutJson(stdout: string): { ok?: boolean } | null {
  const lines = stdout.trim().split(/\r?\n/).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    try {
      return JSON.parse(lines[i]!) as { ok?: boolean };
    } catch {
      /* try previous line */
    }
  }
  return null;
}

function runPy(root: string, args: string[], timeoutMs = 90_000): { status: number; stdout: string; stderr: string } {
  const py = process.env.MKM_PYTHON?.trim() || "py";
  const child = spawnSync(py, args, {
    cwd: root,
    encoding: "utf-8",
    maxBuffer: 8 * 1024 * 1024,
    timeout: timeoutMs,
    windowsHide: true,
  });
  return {
    status: child.status ?? 1,
    stdout: child.stdout || "",
    stderr: child.stderr || "",
  };
}

export function runAthena100ptFromSlug(
  req: Athena100ptChainRequest,
  workspaceRoot?: string,
): Athena100ptChainResult {
  const root = workspaceRoot?.trim() || resolveMkmWorkspaceRoot();
  if (!root) {
    return { ok: false, error: "MKM_WORKSPACE_ROOT not set or han_physician builder missing" };
  }

  const slug = req.slug.trim();
  if (!slug) return { ok: false, error: "missing_slug" };

  const buildScript = path.join(root, "scripts", "build_han_physician_clinical_assist_turn_v1.py");
  const renderScript = path.join(root, "scripts", "render_athena_100pt_from_han_turn_v1.py");
  if (!fs.existsSync(buildScript) || !fs.existsSync(renderScript)) {
    return { ok: false, error: "han_physician or athena_100pt scripts missing in workspace" };
  }

  const buildArgs = [buildScript, "--slug", slug];
  if (req.validateSchema !== false) buildArgs.push("--validate-schema");
  if (req.updatePointer) buildArgs.push("--update-pointer");

  const build = runPy(root, buildArgs);
  if (build.status !== 0) {
    return {
      ok: false,
      error: (build.stderr || build.stdout || `build exit ${build.status}`).trim().slice(0, 3000),
      stderr: build.stderr,
    };
  }

  const hanTurnJson = path.join(root, "reports", `${slug}_han_physician_assist_turn_v1.json`);
  const hanTurnMd = path.join(root, "reports", `${slug}_han_physician_assist_turn_v1.md`);
  if (!fs.existsSync(hanTurnJson)) {
    return { ok: false, error: `han turn json missing: ${hanTurnJson}` };
  }

  const renderArgs = [
    renderScript,
    "--han-turn-json",
    hanTurnJson,
    "--validate-schema",
  ];
  if (req.writeLatest !== false) renderArgs.push("--write-latest");
  if (req.updatePointer) renderArgs.push("--update-pointer");

  const render = runPy(root, renderArgs);
  if (render.status !== 0) {
    return {
      ok: false,
      error: (render.stderr || render.stdout || `render exit ${render.status}`).trim().slice(0, 3000),
      stderr: render.stderr,
    };
  }

  const parsed = parseStdoutJson(render.stdout);
  const reportMd = parsed && "out_md" in parsed ? String((parsed as { out_md?: string }).out_md) : "";
  const reportJson =
    parsed && "out_json" in parsed ? String((parsed as { out_json?: string }).out_json) : "";
  const reportMdPath = reportMd || path.join(root, "reports", `${slug}_athena_100pt_v1.md`);
  const reportJsonPath = reportJson || path.join(root, "reports", `${slug}_athena_100pt_v1.json`);

  if (!fs.existsSync(reportMdPath)) {
    return { ok: false, error: `athena 100pt md missing: ${reportMdPath}` };
  }

  const reportMdContent = fs.readFileSync(reportMdPath, "utf-8");

  return {
    ok: true,
    slug,
    hanTurnJson,
    hanTurnMd,
    reportJson: reportJsonPath,
    reportMd: reportMdPath,
    reportMdContent,
  };
}

export function appendChatTranscriptToMd(md: string, turns: { role: string; message: string }[]): string {
  if (!turns.length) return md;
  const lines = [
    "",
    "## 대화 부록 (Track B · 비구조)",
    "",
    "_아래는 /clinician 채팅 로그 요약입니다. han_physician turn 본문과 별도이며 원장 확정 전 참고용입니다._",
    "",
  ];
  for (const t of turns.slice(-20)) {
    const who = t.role === "assistant" ? "보조" : "원장";
    lines.push(`- **${who}:** ${t.message.replace(/\s+/g, " ").trim().slice(0, 2000)}`);
  }
  lines.push("");
  return `${md.trimEnd()}\n${lines.join("\n")}`;
}
