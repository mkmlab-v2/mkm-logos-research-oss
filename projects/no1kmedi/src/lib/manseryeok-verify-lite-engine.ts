/**
 * VPS / local Python engine — ask-one dual verify + myeongni lite bundle.
 */
import path from "node:path";
import { promises as fs } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export type VerifyLiteBody = {
  birth_instant_utc?: string;
  year?: number;
  month?: number;
  day?: number;
  hour?: number;
  minute?: number;
  tz?: string;
  is_solar?: boolean;
  is_male?: boolean;
  secondary_day_rollover_policy?: "midnight_00" | "zi_23";
};

export type VerifyLiteResponse = {
  gate_status: string;
  policy_interpretation: string;
  reasons: string[];
  timezone_meta: Record<string, unknown>;
  primary: Record<string, unknown> | null;
  secondary: Record<string, unknown> | null;
  myeongni_lite: Record<string, unknown> | null;
  source?: string;
};

function resolvePythonExecutable(): string {
  const fromEnv = process.env.MANSERYEOK_PYTHON?.trim() || process.env.SAJU_VERIFY_PYTHON?.trim();
  if (fromEnv) return fromEnv;
  return process.platform === "win32" ? "py" : "python3";
}

export async function resolveWorkspaceRoot(): Promise<string | null> {
  const fromEnv = process.env.MKM_WORKSPACE_ROOT?.trim();
  if (fromEnv) {
    const abs = path.resolve(fromEnv);
    try {
      await fs.access(path.join(abs, "scripts", "saju_askone_verify_bundle_v1.py"));
      return abs;
    } catch {
      return null;
    }
  }
  const cwd = process.cwd();
  const candidates = [
    cwd,
    path.resolve(cwd, ".."),
    path.resolve(cwd, "..", ".."),
    path.resolve(cwd, "..", "..", ".."),
    path.resolve(cwd, "..", "..", "..", ".."),
  ];
  for (const root of candidates) {
    try {
      await fs.access(path.join(root, "scripts", "saju_askone_verify_bundle_v1.py"));
      return root;
    } catch {
      /* try next */
    }
  }
  return null;
}

function buildArgs(script: string, body: VerifyLiteBody): string[] {
  const utc =
    typeof body.birth_instant_utc === "string" && body.birth_instant_utc.trim().length > 0;
  const args = [script];
  if (utc) {
    args.push("--birth-instant-utc", String(body.birth_instant_utc).trim());
  } else {
    args.push(
      "--year",
      String(body.year),
      "--month",
      String(body.month),
      "--day",
      String(body.day),
      "--hour",
      String(body.hour),
      "--minute",
      String(body.minute ?? 0),
    );
  }
  args.push("--tz", String(body.tz ?? "Asia/Seoul"));
  if (body.is_solar === false) args.push("--no-solar");
  else args.push("--solar");
  if (body.is_male === false) args.push("--female");
  else args.push("--male");
  args.push(
    "--secondary-day-rollover-policy",
    String(body.secondary_day_rollover_policy ?? "midnight_00"),
  );
  return args;
}

export async function runVerifyLiteEngine(body: VerifyLiteBody): Promise<VerifyLiteResponse> {
  const root = await resolveWorkspaceRoot();
  if (!root) {
    throw new Error("workspace_root_not_found");
  }
  const script = path.join(root, "scripts", "saju_askone_verify_bundle_v1.py");
  const py = resolvePythonExecutable();
  const { stdout } = await execFileAsync(py, buildArgs(script, body), {
    cwd: root,
    windowsHide: true,
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(stdout) as VerifyLiteResponse;
}
