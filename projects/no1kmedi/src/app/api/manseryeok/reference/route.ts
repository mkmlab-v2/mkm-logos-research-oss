/**
 * jema-ai.com — POST /api/manseryeok/reference
 * Proxies workspace Python engine; repo path projects/no1kmedi (do not confuse with public domain string).
 */
import { NextResponse } from "next/server";
import path from "node:path";
import { promises as fs } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { looksLikeIsoInstant } from "@/lib/global-birth-input";

const execFileAsync = promisify(execFile);

function resolvePythonExecutable(): string {
  const fromEnv = process.env.MANSERYEOK_PYTHON?.trim();
  if (fromEnv) return fromEnv;
  return process.platform === "win32" ? "py" : "python3";
}

async function resolveWorkspaceRoot(): Promise<string | null> {
  const fromEnv = process.env.MKM_WORKSPACE_ROOT?.trim();
  if (fromEnv) {
    const abs = path.resolve(fromEnv);
    try {
      await fs.access(path.join(abs, "scripts", "run_saju_global_birth_v1.py"));
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
      await fs.access(path.join(root, "scripts", "run_saju_global_birth_v1.py"));
      return root;
    } catch {
      /* try next */
    }
  }
  return null;
}

function buildSajuLabelFromEngineDoc(fullSaju: unknown): string {
  if (!fullSaju || typeof fullSaju !== "object") return "";
  const row = fullSaju as { saju?: Record<string, unknown> };
  const s = row.saju;
  if (!s || typeof s !== "object") return "";
  const y = String(s.year ?? "").trim();
  const m = String(s.month ?? "").trim();
  const d = String(s.day ?? "").trim();
  const h = String(s.hour ?? "").trim();
  if (!y || !m || !d || !h) return "";
  return `연월일시 기둥 · 년:${y} 월:${m} 일:${d} 시:${h}`;
}

type ReferenceBody = {
  birth_instant_utc?: string;
  iana_tz?: string;
  birth_datetime?: string;
  is_male?: boolean;
};

function unauthorized(): NextResponse {
  return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
}

export async function POST(req: Request) {
  const guard = process.env.MANSERYEOK_REFERENCE_TOKEN?.trim();
  if (guard) {
    const token = req.headers.get("x-api-token")?.trim();
    if (!token || token !== guard) return unauthorized();
  }

  let body: ReferenceBody;
  try {
    body = (await req.json()) as ReferenceBody;
  } catch {
    return NextResponse.json({ success: false, error: "invalid_json" }, { status: 400 });
  }

  const utc = typeof body.birth_instant_utc === "string" ? body.birth_instant_utc.trim() : "";
  const tz = typeof body.iana_tz === "string" ? body.iana_tz.trim() : "";

  if (!utc || !tz) {
    return NextResponse.json(
      {
        success: false,
        error: "birth_instant_utc_and_iana_tz_required",
        hint: "엔진 프록시는 절대시각+IANA만 지원합니다. 레거시 birth_datetime만 있는 경우 외부 스텁을 쓰세요.",
      },
      { status: 422 },
    );
  }
  if (!looksLikeIsoInstant(utc)) {
    return NextResponse.json({ success: false, error: "invalid_birth_instant_utc" }, { status: 400 });
  }

  const root = await resolveWorkspaceRoot();
  if (!root) {
    return NextResponse.json(
      {
        success: false,
        error: "workspace_root_not_found",
        hint: "Set MKM_WORKSPACE_ROOT to the monorepo root containing scripts/run_saju_global_birth_v1.py",
      },
      { status: 503 },
    );
  }

  const script = path.join(root, "scripts", "run_saju_global_birth_v1.py");
  const args = [
    script,
    "--utc-instant",
    utc,
    "--iana-tz",
    tz,
    "--compact",
    ...(body.is_male === true ? ["--is-male"] : []),
  ];

  try {
    const py = resolvePythonExecutable();
    const { stdout, stderr } = await execFileAsync(py, args, {
      cwd: root,
      windowsHide: true,
      maxBuffer: 8 * 1024 * 1024,
    });
    if (stderr && process.env.NODE_ENV !== "production") {
      console.warn("[manseryeok/reference] stderr:", stderr.slice(0, 500));
    }
    const doc = JSON.parse(stdout) as { full_saju?: unknown };
    const label = buildSajuLabelFromEngineDoc(doc.full_saju);
    if (!label) {
      return NextResponse.json(
        { success: false, error: "engine_parse_failed", hint: "PerfectManseryeok output missing saju pillars" },
        { status: 500 },
      );
    }
    return NextResponse.json(
      {
        success: true,
        saju_label: label,
        source: "workspace-engine",
        engine: "PerfectManseryeok",
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    const stderr =
      err && typeof err === "object" && "stderr" in err ? String((err as { stderr?: unknown }).stderr ?? "") : "";
    console.error("[manseryeok/reference]", msg, stderr.slice(0, 800));
    return NextResponse.json(
      {
        success: false,
        error: "engine_runtime_error",
        message: msg.slice(0, 400),
      },
      { status: 500 },
    );
  }
}
