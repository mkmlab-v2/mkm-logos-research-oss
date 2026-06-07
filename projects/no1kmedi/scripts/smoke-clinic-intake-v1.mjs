#!/usr/bin/env node
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";
const ADMIN_TOKEN = (process.env.NO1KMEDI_ADMIN_TOKEN || "").trim();

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

async function main() {
  const patientName = "스모크테스트";
  const patientPhone = "010-1234-5678";

  const submit = await request("/api/intake/clinic-intake-v1", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      schema_version: "clinic_intake_v1",
      patient: {
        name: patientName,
        phone: patientPhone,
        birthdate: "1990-01-01",
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
        severity_nrs: 5,
        free_text: "테스트 입력",
      },
      health_core: {
        sleep_quality: "보통",
        bowel_pattern: "규칙적",
        appetite: "정상",
        stress_level: 4,
        medications: "",
      },
      constitution: {
        body_frame: "균형형",
        heat_cold_sensitivity: "비슷함",
        temperament: "상황에 따라 다름",
        digestion_pattern: "불규칙함",
        fatigue_recovery: "중간",
      },
      clinic_preference: {
        region: "광명",
        specialty: "sleep",
        preferred_time: "weekday_evening",
      },
      optional_profile: {
        birth_time: "09:30",
        birth_time_known: true,
      },
      submitted_at_utc: new Date().toISOString(),
    }),
  });

  assert(submit.res.status === 200, `clinic-intake-v1 POST expected 200, got ${submit.res.status}`);
  assert(submit.json?.success === true, "clinic-intake-v1 POST success must be true");
  assert(typeof submit.json?.survey_id === "string" && submit.json.survey_id.length > 0, "survey_id required");
  assert(typeof submit.json?.intake_pin === "string" && submit.json.intake_pin.length >= 6, "intake_pin required");
  assert(["routine", "priority", "emergency"].includes(submit.json?.triage_level), "triage_level invalid");
  assert(submit.json?.kakao_summary?.receipt_id === submit.json?.survey_id, "kakao_summary.receipt_id mismatch");
  assert(submit.json?.birth_resolved === true, "birth_resolved must be true when birthdate provided");
  assert(typeof submit.json?.birth_resolved === "boolean", "birth_resolved field required");

  const intakePin = submit.json.intake_pin;
  const pinLookup = await request(
    `/api/intake/patient-presurvey?pin=${encodeURIComponent(intakePin)}&name=${encodeURIComponent(patientName)}`,
    { method: "GET" },
  );
  assert(pinLookup.res.status === 200, `PIN lookup expected 200, got ${pinLookup.res.status}`);
  assert(pinLookup.json?.success === true, "PIN lookup success must be true");
  assert(pinLookup.json?.survey?.lane_a_profile?.birth_instant_utc, "PIN lookup must return birth_instant_utc");
  assert(pinLookup.json?.survey?.lane_a_profile?.iana_tz === "Asia/Seoul", "PIN lookup iana_tz must be Asia/Seoul");

  const list = await request("/api/intake/clinic-intake-v1", {
    method: "GET",
    headers: ADMIN_TOKEN ? { "x-no1kmedi-admin-token": ADMIN_TOKEN } : {},
  });
  if (list.res.status === 401) {
    console.log("clinic-intake-v1 GET skipped (admin token required)");
  } else {
    assert(list.res.status === 200, `clinic-intake-v1 GET expected 200, got ${list.res.status}`);
    assert(list.json?.success === true, "clinic-intake-v1 GET success must be true");
    assert(Array.isArray(list.json?.rows), "clinic-intake-v1 GET rows must be array");
  }

  console.log("smoke-clinic-intake-v1 passed");
}

main().catch((error) => {
  console.error("smoke-clinic-intake-v1 failed:", error.message);
  process.exit(1);
});
