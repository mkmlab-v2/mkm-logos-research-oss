#!/usr/bin/env node
/**
 * HTTP: advanced-consult (validate envelope) → patient-care-bundle-from-cds (MD preview).
 * Requires dev server: npm run dev (port 3010) and MKM_WORKSPACE_ROOT on the Next process.
 *
 *   MKM_WORKSPACE_ROOT=C:\workspace npm run smoke:clinician-cds-bundle-http
 * Optional: KM_PATIENT_CARE_BUNDLE_TOKEN + KM_PATIENT_CARE_BUNDLE_TRUST_SAME_ORIGIN=1 for token+UI parity.
 */

const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";
const REQUIRE_VALIDATE =
  process.argv.includes("--require-validate") || process.env.NO1KMEDI_REQUIRE_KM_CDS_VALIDATE === "1";
const BUNDLE_TOKEN = (process.env.KM_PATIENT_CARE_BUNDLE_TOKEN || "").trim();

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

function buildConsultPayload() {
  return {
    schema: "patient_consult_input_v1",
    request_id: `http_bundle_${Date.now()}`,
    actor_id: "hanui-smoke-bundle",
    lane_a_profile: {
      birth_instant_utc: "1987-12-31T15:00:00Z",
      iana_tz: "Asia/Seoul",
      constitution_survey: { digestion_pattern: "식후 더부룩함" },
    },
    lane_b_clinical: {
      chief_complaint: "만성 피로",
      onset: "6개월",
      severity: "중등도",
      medication: "없음",
      health_survey: { sleep_quality: "입면 지연" },
    },
  };
}

function soapStubFromDraft(draft) {
  return {
    subjective: { text: draft.clinical_summary || "CDSS 임상 요약" },
    objective: { text: "진찰·맥진 확정 후 갱신." },
    assessment: { text: draft.reasoning?.syndrome_hypothesis || "변증 가설" },
    plan: { text: draft.reasoning?.care_direction || "계획 초안" },
  };
}

async function main() {
  let consult;
  try {
    consult = await request("/api/cdss/advanced-consult?validate_km_cds_envelope=1", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Origin: BASE_URL,
        Referer: `${BASE_URL}/clinician`,
      },
      body: JSON.stringify(buildConsultPayload()),
    });
  } catch (err) {
    console.error(
      `smoke-clinician-cds-bundle-http: SKIP (server unreachable at ${BASE_URL}). Start: npm run dev`,
    );
    console.error(String(err?.message || err));
    process.exit(0);
  }

  assert(consult.res.status === 200, `advanced-consult expected 200, got ${consult.res.status}`);
  assert(consult.json?.success === true, "advanced-consult success");
  const km = consult.json?.km_cds;
  assert(km && typeof km === "object", "km_cds required");
  if (REQUIRE_VALIDATE) {
    assert(km.validation?.ok === true, `km_cds.validation.ok required (--require-validate): ${km.validation?.error || km.validation?.method}`);
    assert(km.envelope?.schema === "km_physician_cds_assist_envelope_v1", "km_cds.envelope schema");
  }
  if (km.validation?.ok === true) {
    assert(km.envelope != null, "envelope when validation ok");
  } else {
    console.warn(
      `warn: km_cds.validation not ok (method=${km.validation?.method}); bundle step may be skipped. Set MKM_WORKSPACE_ROOT on Next dev.`,
    );
    if (REQUIRE_VALIDATE) process.exit(1);
    return;
  }

  const draft = consult.json.draft;
  const headers = {
    "Content-Type": "application/json",
    Origin: BASE_URL,
    Referer: `${BASE_URL}/clinician`,
  };
  if (BUNDLE_TOKEN) headers["x-api-token"] = BUNDLE_TOKEN;

  const bundle = await request("/api/cdss/patient-care-bundle-from-cds", {
    method: "POST",
    headers,
    body: JSON.stringify({
      schema: "patient_care_bundle_from_cds_request_v1",
      request_id: draft.request_id,
      birth_instant_utc: "1987-12-31T15:00:00Z",
      iana_tz: "Asia/Seoul",
      cds_envelope: km.envelope,
      soap: soapStubFromDraft(draft),
      options: {
        apply_slot_templates: true,
        validate_policy: true,
        validate_bundle: true,
        render_patient_md: true,
      },
    }),
  });

  assert(bundle.res.status === 200, `bundle expected 200, got ${bundle.res.status}: ${bundle.json?.error || bundle.json?.detail}`);
  assert(bundle.json?.success === true, "bundle success");
  assert(bundle.json?.patient_care_bundle?.schema === "patient_care_bundle_v1", "bundle schema");
  assert(bundle.json?.boundary?.physician_confirmation_required === true, "physician boundary");
  const md = bundle.json?.patient_facing_markdown;
  assert(typeof md === "string" && md.trim().length > 20, "patient_facing_markdown");

  console.log(
    `smoke-clinician-cds-bundle-http: OK bundle_id=${bundle.json.patient_care_bundle?.bundle_id || "n/a"} md_chars=${md.length}`,
  );
}

main().catch((error) => {
  console.error("smoke-clinician-cds-bundle-http failed:", error.message);
  process.exit(1);
});
