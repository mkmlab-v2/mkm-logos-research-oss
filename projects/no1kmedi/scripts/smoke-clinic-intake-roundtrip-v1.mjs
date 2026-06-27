#!/usr/bin/env node
/**
 * Intake wizard dry-run: POST clinic-intake-v1 → PIN lookup → clinician handoff fields.
 */
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function request(path, init) {
  const res = await fetch(`${BASE_URL}${path}`, init);
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    json = { raw: text };
  }
  return { res, json };
}

function applyPinToClinicianState(survey) {
  const qa = survey.constitution_survey?.questionnaire_answers || {};
  const heatCold = qa.heat_cold_sensitivity || "";
  const fatigue = qa.fatigue_recovery || "";
  const constitutionNotes = [heatCold && `한·냉: ${heatCold}`, fatigue && `피로 회복: ${fatigue}`]
    .filter(Boolean)
    .join(" · ");
  const mergedComplaint = [survey.symptoms?.pain_area, survey.symptoms?.consultation_goal].filter(Boolean).join(" / ");
  return {
    chiefComplaint: mergedComplaint || survey.symptoms?.pain_area || "",
    onset: survey.symptoms?.symptom_duration || "",
    severity: `${survey.symptoms?.pain_scale_0_10}/10`,
    digestionPattern: survey.constitution_survey?.digestion_pattern || "",
    sleepPattern: survey.constitution_survey?.sleep_pattern || "",
    painScale0to10: String(survey.symptoms?.pain_scale_0_10 ?? ""),
    bodyHeatPreference: heatCold,
    constitutionFreeText: constitutionNotes,
    birthInstantUtc: survey.lane_a_profile?.birth_instant_utc || "",
    ianaTz: survey.lane_a_profile?.iana_tz || "Asia/Seoul",
    loadedSurveyContext: {
      surveyId: survey.survey_id,
      intakePin: survey.intake_pin,
      patientName: survey.patient_name,
      triageLevel: survey.triage_level,
    },
  };
}

async function main() {
  const patientName = "드라이런환자";
  const patientPhone = "010-9876-5432";

  const submit = await request("/api/intake/clinic-intake-v1", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      schema_version: "clinic_intake_v1",
      patient: {
        name: patientName,
        phone: patientPhone,
        birthdate: "1985-06-15",
        visit_type: "초진",
      },
      consent: {
        sensitive_collection: true,
        kakao_transfer: true,
        non_diagnostic_notice: true,
      },
      red_flags: {
        chestPain: false,
        neuroDeficit: false,
        highFever: false,
        pregnancyOrMajorCondition: false,
      },
      symptom: {
        main_symptom: "수면/피로",
        duration: "1주~1개월",
        severity_nrs: 6,
        free_text: "드라이런 테스트",
      },
      health_core: {
        sleep_quality: "보통",
        bowel_pattern: "규칙적",
        appetite: "정상",
        stress_level: 5,
        medications: "",
      },
      constitution: {
        body_frame: "균형형",
        heat_cold_sensitivity: "추위를 더 탐",
        temperament: "상황에 따라 다름",
        digestion_pattern: "식후 더부룩함",
        fatigue_recovery: "휴식해도 오래 감",
      },
      clinic_preference: {
        region: "광명",
        specialty: "sleep",
        preferred_time: "weekday_evening",
      },
      optional_profile: {
        birth_time: "14:30",
        birth_time_known: true,
      },
      submitted_at_utc: new Date().toISOString(),
    }),
  });

  assert(submit.res.status === 200, `intake POST expected 200, got ${submit.res.status}`);
  assert(submit.json?.success === true, "intake POST success");
  const intakePin = submit.json?.intake_pin;
  assert(typeof intakePin === "string" && intakePin.length >= 6, "intake_pin required");

  const pinLookup = await request(
    `/api/intake/patient-presurvey?pin=${encodeURIComponent(intakePin)}&name=${encodeURIComponent(patientName)}`,
    { method: "GET" },
  );
  assert(pinLookup.res.status === 200, `PIN lookup expected 200, got ${pinLookup.res.status}`);
  assert(pinLookup.json?.success === true, "PIN lookup success");
  const survey = pinLookup.json?.survey;
  assert(survey?.intake_pin === intakePin, "PIN mismatch");
  assert(survey?.patient_name === patientName, "patient_name mismatch");
  assert(survey?.symptoms?.pain_area, "symptoms.pain_area required");

  const clinicianState = applyPinToClinicianState(survey);
  assert(clinicianState.loadedSurveyContext.intakePin === intakePin, "clinician handoff PIN");
  assert(clinicianState.chiefComplaint.includes("수면"), "chiefComplaint must include symptom");
  assert(clinicianState.bodyHeatPreference.includes("추위"), "bodyHeatPreference from constitution");
  assert(clinicianState.birthInstantUtc, "birth_instant_utc required for clinician panel");

  const path = await import("node:path");
  const fs = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const defaultOut = path.resolve(scriptDir, "../../../reports/patient_intake_roundtrip_dry_v1_latest.json");
  const outPath = (process.env.PATIENT_INTAKE_ROUNDTRIP_OUT || defaultOut).trim();

  const report = {
    ok: true,
    schema: "patient_intake_roundtrip_dry_v1",
    generated_at_utc: new Date().toISOString(),
    base_url: BASE_URL,
    intake_pin: intakePin,
    survey_id: survey.survey_id,
    triage_level: survey.triage_level,
    clinician_handoff: clinicianState,
    reproduce: "cd projects/no1kmedi && npm run smoke:clinic-intake-roundtrip",
  };
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");

  console.log(
    JSON.stringify({
      ok: true,
      intake_pin: intakePin,
      triage_level: survey.triage_level,
      clinician_chief_complaint: clinicianState.chiefComplaint,
    }),
  );
  console.log("smoke-clinic-intake-roundtrip-v1 passed");
}

main().catch((error) => {
  console.error("smoke-clinic-intake-roundtrip-v1 failed:", error.message);
  process.exit(1);
});
