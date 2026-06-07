import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import { access } from "node:fs/promises";

const execFileAsync = promisify(execFile);

function resolvePythonExecutable() {
  const fromEnv = (process.env.MANSERYEOK_PYTHON || process.env.SAJU_VERIFY_PYTHON || "").trim();
  if (fromEnv) return fromEnv;
  return process.platform === "win32" ? "py" : "python3";
}

async function resolveWorkspaceRoot() {
  const fromEnv = (process.env.MKM_WORKSPACE_ROOT || "").trim();
  if (fromEnv) {
    const abs = path.resolve(fromEnv);
    await access(path.join(abs, "scripts", "saju_askone_verify_bundle_v1.py"));
    return abs;
  }
  throw new Error("workspace_root_not_found");
}

function buildBundleArgs(script, body) {
  const utc =
    typeof body.birth_instant_utc === "string" && body.birth_instant_utc.trim().length > 0;
  const args = [script];
  if (utc) {
    args.push("--birth-instant-utc", body.birth_instant_utc.trim());
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
  args.push("--tz", String(body.tz || "Asia/Seoul"));
  if (body.is_solar === false) args.push("--no-solar");
  else args.push("--solar");
  if (body.is_male === false) args.push("--female");
  else args.push("--male");
  args.push(
    "--secondary-day-rollover-policy",
    String(body.secondary_day_rollover_policy || "midnight_00"),
  );
  return args;
}

export async function runVerifyLiteEngine(body) {
  const root = await resolveWorkspaceRoot();
  const script = path.join(root, "scripts", "saju_askone_verify_bundle_v1.py");
  const py = resolvePythonExecutable();
  const { stdout } = await execFileAsync(py, buildBundleArgs(script, body), {
    cwd: root,
    windowsHide: true,
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(stdout);
}
