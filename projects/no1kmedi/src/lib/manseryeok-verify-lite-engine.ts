/**
 * VPS / local Python engine — ask-one dual verify + myeongni lite bundle.
 */
import path from "node:path";
import { promises as fs } from "node:fs";
import { execFile, spawn } from "node:child_process";
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

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/** y/m/d/h → ISO UTC (Asia/Seoul wall +09 when tz is Seoul). */
export function resolveVerifyLiteBirthInstantUtc(body: VerifyLiteBody): string | null {
  const direct = body.birth_instant_utc?.trim();
  if (direct) return direct;
  if (
    body.year == null ||
    body.month == null ||
    body.day == null ||
    body.hour == null
  ) {
    return null;
  }
  const tz = (body.tz ?? "Asia/Seoul").trim();
  const minute = body.minute ?? 0;
  const offset = tz === "Asia/Seoul" ? "+09:00" : "+00:00";
  const localIso = `${body.year}-${pad2(body.month)}-${pad2(body.day)}T${pad2(body.hour)}:${pad2(minute)}:00${offset}`;
  const instant = new Date(localIso);
  if (Number.isNaN(instant.getTime())) return null;
  return instant.toISOString();
}

export function withBirthInstantUtc(body: VerifyLiteBody): VerifyLiteBody {
  const birth_instant_utc = resolveVerifyLiteBirthInstantUtc(body);
  if (!birth_instant_utc) return body;
  return { ...body, birth_instant_utc };
}

export async function runMyeongniLiteEnrichEngine(input: {
  birth_instant_utc: string;
  iana_tz: string;
  is_male?: boolean;
}): Promise<Record<string, unknown>> {
  const root = await resolveWorkspaceRoot();
  if (!root) {
    throw new Error("workspace_root_not_found");
  }
  const script = path.join(root, "scripts", "saju_myeongni_lite_enrich_v1.py");
  const py = resolvePythonExecutable();
  const args = [
    script,
    "--birth-instant-utc",
    input.birth_instant_utc,
    "--iana-tz",
    input.iana_tz,
  ];
  if (input.is_male === false) args.push("--female");
  else args.push("--is-male");
  const { stdout } = await execFileAsync(py, args, {
    cwd: root,
    windowsHide: true,
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(stdout) as Record<string, unknown>;
}

export async function runVerifyLiteEngine(body: VerifyLiteBody): Promise<VerifyLiteResponse> {
  const root = await resolveWorkspaceRoot();
  if (!root) {
    throw new Error("workspace_root_not_found");
  }
  const script = path.join(root, "scripts", "saju_askone_verify_bundle_v1.py");
  const py = resolvePythonExecutable();
  const normalized = withBirthInstantUtc(body);
  const { stdout } = await execFileAsync(py, buildArgs(script, normalized), {
    cwd: root,
    windowsHide: true,
    maxBuffer: 8 * 1024 * 1024,
  });
  const doc = JSON.parse(stdout) as VerifyLiteResponse;
  if (!doc.myeongni_lite && normalized.birth_instant_utc) {
    try {
      doc.myeongni_lite = await runMyeongniLiteEnrichEngine({
        birth_instant_utc: normalized.birth_instant_utc,
        iana_tz: String(body.tz ?? "Asia/Seoul"),
        is_male: body.is_male,
      });
    } catch {
      /* keep null lite */
    }
  }
  return doc;
}

export async function runMyeongniFullReportEngine(body: VerifyLiteBody): Promise<Record<string, unknown>> {
  const root = await resolveWorkspaceRoot();
  if (!root) {
    throw new Error("workspace_root_not_found");
  }
  if (body.year == null || body.month == null || body.day == null || body.hour == null) {
    throw new Error("birth_fields_required_for_full_report");
  }
  const script = path.join(root, "scripts", "build_myeongni_full_report_v1.py");
  const py = resolvePythonExecutable();
  const args = [
    script,
    "--local",
    String(body.year),
    String(body.month),
    String(body.day),
    String(body.hour),
    String(body.minute ?? 0),
    "0",
    "--iana-tz",
    String(body.tz ?? "Asia/Seoul"),
    "--annual-years",
    "3",
    "--monthly-months-per-year",
    "1",
  ];
  if (body.is_male !== false) args.push("--is-male");
  const { stdout } = await execFileAsync(py, args, {
    cwd: root,
    windowsHide: true,
    maxBuffer: 16 * 1024 * 1024,
  });
  return JSON.parse(stdout) as Record<string, unknown>;
}

export async function renderMyeongniFullReportMarkdown(
  report: Record<string, unknown>,
): Promise<string> {
  const root = await resolveWorkspaceRoot();
  if (!root) {
    throw new Error("workspace_root_not_found");
  }
  const script = path.join(root, "scripts", "render_myeongni_full_report_markdown_v1.py");
  const py = resolvePythonExecutable();
  const input = JSON.stringify(report);
  return new Promise((resolve, reject) => {
    const child = spawn(py, [script], {
      cwd: root,
      windowsHide: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    const chunks: Buffer[] = [];
    let stderr = "";
    child.stdout.on("data", (chunk) => chunks.push(Buffer.from(chunk)));
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `render_myeongni_full_report exit ${code}`));
        return;
      }
      resolve(Buffer.concat(chunks).toString("utf8"));
    });
    child.stdin.write(input, "utf8");
    child.stdin.end();
  });
}

export function summarizeMyeongniFullReport(report: Record<string, unknown>): Record<string, unknown> {
  const pillars = report.pillars;
  const structure = report.structure_analysis;
  const daewoon = report.daewoon;
  const annual = report.annual_fortune;
  let annualRows: unknown = null;
  if (Array.isArray(annual)) {
    annualRows = annual.slice(0, 3);
  } else if (annual && typeof annual === "object") {
    const rows = (annual as Record<string, unknown>).rows;
    annualRows = Array.isArray(rows) ? rows.slice(0, 3) : null;
  }
  let yongsinHeadline: unknown = null;
  if (structure && typeof structure === "object") {
    const s = structure as Record<string, unknown>;
    yongsinHeadline = s.yongsin_hypothesis ?? s.strength_label ?? null;
  }
  return {
    schema: report.schema ?? "myeongni_full_report_v1",
    pillars_native: pillars ?? null,
    structure_analysis: structure ?? null,
    yongsin_hypothesis_headline: yongsinHeadline,
    daewoon_headline: daewoon ?? null,
    annual_rows: annualRows,
    send_gate: "HOLD",
    research_only: true,
    non_gating: true,
  };
}
