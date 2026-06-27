#!/usr/bin/env node
/**
 * Offline smoke: intake paste → build_patient_intake_fusion_draft_v1 (lee_heecheol).
 * No Next server. Requires py + jsonschema + workspace reports.
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

  const runDir = path.join(monoRoot, "reports", "cdss_runtime", "smoke_intake_fusion_lee_heecheol");
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
      subjective_notes: "카톡 paste smoke: 복부 팽만·피로 호소",
      sasang_estimate: { label: "태음인 가능성", source: "smoke_v1" },
    },
  };

  const intakePath = path.join(runDir, "intake.json");
  const bundleOut = path.join(runDir, "bundle.json");
  const myeongniOut = path.join(runDir, "myeongni.json");
  const rationaleOut = path.join(runDir, "rationale.json");
  fs.writeFileSync(intakePath, JSON.stringify(intake, null, 2));

  const py = process.env.MKM_PYTHON || "py";
  const script = path.join(monoRoot, "scripts", "build_patient_intake_fusion_draft_v1.py");
  const child = spawnSync(
    py,
    [
      script,
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

  if (child.status !== 0) {
    throw new Error((child.stderr || child.stdout || `exit ${child.status}`).slice(0, 2000));
  }

  const bundle = JSON.parse(fs.readFileSync(bundleOut, "utf8"));
  assert(bundle.schema === "patient_care_bundle_v1", `bundle schema ${bundle.schema}`);
  assert(bundle.clinical_soap_v1?.subjective?.text, "SOAP subjective missing");

  console.log("smoke-clinician-intake-fusion-draft-offline: OK lee_heecheol");
}

main();
