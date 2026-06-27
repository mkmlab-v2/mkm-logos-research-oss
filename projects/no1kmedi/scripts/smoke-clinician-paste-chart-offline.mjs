#!/usr/bin/env node
/**
 * Offline smoke: Paste Chart v1 — fusion bundle + IWS copilot chain (lee_heecheol).
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const monoRoot = path.resolve(__dirname, "..", "..", "..");

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function parseBirthdate(birthInstant) {
  const d = new Date(birthInstant);
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return fmt.format(d);
}

function chiefFromPaste(text) {
  const line = text.split("\n").map((l) => l.trim()).find(Boolean) || text.trim();
  return line.slice(0, 800);
}

function main() {
  const pointerPath = path.join(monoRoot, "reports", "lee_heecheol_intake_ssot_pointer_v1.json");
  const trackBPath = path.join(monoRoot, "reports", "lee_heecheol_patient_track_b_memory_v1.json");
  assert(fs.existsSync(pointerPath), "lee_heecheol pointer missing");
  assert(fs.existsSync(trackBPath), "lee_heecheol track_b memory missing");

  const pointer = JSON.parse(fs.readFileSync(pointerPath, "utf8"));
  const trackB = JSON.parse(fs.readFileSync(trackBPath, "utf8"));
  const birthLocal = trackB.profile?.birth_local;
  assert(birthLocal, "birth_local missing");
  const birthInstant = new Date(birthLocal).toISOString();
  const chartText = "식후 더부룩함 2주 · 피로 · 야식 잦음 · 복부 팽만";

  const runDir = path.join(monoRoot, "reports", "cdss_runtime", "smoke_paste_chart_lee_heecheol");
  fs.mkdirSync(runDir, { recursive: true });

  const intake = {
    schema: "patient_intake_fusion_draft_v1",
    version: "1.0.0",
    encounter: { ref_token: pointer.ref_token },
    profile: {
      birth_instant_utc: birthInstant,
      iana_tz: "Asia/Seoul",
      is_male: true,
    },
    intake: {
      symptoms: ["식후 더부룩", "피로", "야식"],
      situation: "당뇨·위축성 위염 추적 중",
      subjective_notes: chartText,
      sasang_estimate: { label: "태음인 가능성", source: "smoke_paste_chart_v1" },
    },
  };

  const intakePath = path.join(runDir, "intake.json");
  const bundleOut = path.join(runDir, "bundle.json");
  const myeongniOut = path.join(runDir, "myeongni.json");
  const rationaleOut = path.join(runDir, "rationale.json");
  fs.writeFileSync(intakePath, JSON.stringify(intake, null, 2));

  const py = process.env.MKM_PYTHON || "py";
  const fusionScript = path.join(monoRoot, "scripts", "build_patient_intake_fusion_draft_v1.py");
  const fusion = spawnSync(
    py,
    [
      fusionScript,
      "--intake-json",
      intakePath,
      "--myeongni-out",
      myeongniOut,
      "--bundle-out",
      bundleOut,
      "--rationale-out",
      rationaleOut,
      "--validate-schema",
      "--validate-policy",
    ],
    { cwd: monoRoot, encoding: "utf-8", timeout: 180_000, windowsHide: true },
  );
  if (fusion.status !== 0) {
    throw new Error((fusion.stderr || fusion.stdout || `fusion exit ${fusion.status}`).slice(0, 2000));
  }

  const bundle = JSON.parse(fs.readFileSync(bundleOut, "utf8"));
  assert(bundle.clinical_soap_v1, "clinical_soap_v1 missing in bundle");

  const iwsDir = path.join(runDir, "iws_copilot");
  fs.mkdirSync(iwsDir, { recursive: true });
  const consult = {
    schema: "patient_consult_input_v1",
    request_id: "smoke_paste_chart_lee_heecheol",
    actor_id: "smoke_paste_chart_v1",
    lane_a_profile: {
      birth_instant_utc: birthInstant,
      iana_tz: "Asia/Seoul",
      constitution_survey: {},
    },
    lane_b_clinical: {
      chief_complaint: chiefFromPaste(chartText),
      onset: "2주",
      severity: "moderate",
      medication: "none_reported",
      health_survey: {},
    },
    sasang_internal: "taeum",
  };
  const consultPath = path.join(iwsDir, "patient_consult.json");
  fs.writeFileSync(consultPath, JSON.stringify(consult, null, 2));

  const publishScript = path.join(monoRoot, "scripts", "publish_integrated_wellness_solution_v2_exports_v1.py");
  const iws = spawnSync(
    py,
    [publishScript, "--out-dir", iwsDir, "--consult-json", consultPath],
    { cwd: monoRoot, encoding: "utf-8", timeout: 120_000, windowsHide: true },
  );
  if (iws.status !== 0) {
    throw new Error((iws.stderr || iws.stdout || `iws exit ${iws.status}`).slice(0, 2000));
  }

  const resolvedPath = path.join(iwsDir, "resolved_latest.json");
  assert(fs.existsSync(resolvedPath), "resolved_latest.json missing");
  const resolved = JSON.parse(fs.readFileSync(resolvedPath, "utf8"));
  assert(resolved && typeof resolved === "object", "resolved payload invalid");

  const apiRoute = path.join(
    monoRoot,
    "projects",
    "no1kmedi",
    "src",
    "app",
    "api",
    "clinician",
    "paste-chart-v1",
    "route.ts",
  );
  assert(fs.existsSync(apiRoute), "paste-chart-v1 API route missing");

  console.log(
    JSON.stringify({
      ok: true,
      smoke: "paste_chart_v1_offline",
      slug: "lee_heecheol",
      birthdate: parseBirthdate(birthInstant),
      soap_keys: Object.keys(bundle.clinical_soap_v1 || {}),
      resolved_keys: Object.keys(resolved).slice(0, 8),
    }),
  );
}

main();
