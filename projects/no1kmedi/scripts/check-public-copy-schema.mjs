#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const copyPath = path.resolve(__dirname, "..", "marketing-site", "public-copy.json");

const requiredPathChecks = [
  "_meta.locale",
  "header.brand_name",
  "header.brand_tagline",
  "seo.title",
  "seo.description",
  "nav.service_group",
  "nav.service_consumer",
  "nav.service_clinician",
  "nav.service_reception",
  "nav.about_group",
  "nav.about",
  "nav.safety",
  "nav.workflow",
  "nav.contact",
  "nav.service_developer",
  "nav.toggle_label",
  "nav.toggle_open_aria",
  "nav.toggle_close_aria",
  "nav.main_aria_label",
  "links.consumer",
  "links.developer",
  "links.clinician",
  "links.reception",
  "links.contact",
  "homepage_a11y.skip_to_main",
  "hero.eyebrow",
  "ring0_identity.schema",
  "ring0_identity.ko.one_liner",
  "ring0_identity.ko.hero.disclaimer",
  "ring0_identity.en.one_liner",
  "validation_engine.seo.title",
  "validation_engine.hero.title",
  "validation_engine.reproduce.gate_command",
  "lane_governance.seo.title",
  "lane_governance.hero.title",
  "lane_governance.firewall.gate_command",
  "links.safety",
  "safety.section_lead",
  "safety.lane_governance_cta.label",
  "safety.lane_governance_cta.href",
  "hero.title",
  "hero.proof_aria_label",
  "hero.subtitle",
  "hero.cta_primary",
  "hero.cta_secondary",
  "hero.cta_tertiary",
  "hero.cta_quaternary",
  "governance_flow.title",
  "governance_flow.section_lead",
  "why_mkm_ai.title",
  "why_mkm_ai.section_lead",
  "why_mkm_ai.disclaimer",
  "quick_start.title",
  "quick_start.section_lead",
  "basic_health_chat.title",
  "basic_health_chat.section_lead",
  "basic_health_chat.assistant_greeting",
  "basic_health_chat.chat.error_message",
  "nav.governance",
  "trust.note",
  "public_solution.title",
  "public_solution.section_lead",
  "clinic_o2o.title",
  "clinic_o2o.section_lead",
  "landing_flow.title",
  "contact.title",
  "paddle_checkout.button_idle",
  "paddle_checkout.hint",
  "paddle_checkout.errors.missing_env",
  "free_validation_lead.title",
  "free_validation_lead.section_lead",
  "free_validation_lead.success",
  "free_validation_lead.errors.required_fields",
  "footer.email",
];

function getByPath(obj, dottedPath) {
  return dottedPath.split(".").reduce((acc, key) => (acc == null ? undefined : acc[key]), obj);
}

function assert(condition, message, errors) {
  if (!condition) errors.push(message);
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function validateLinkTarget(value) {
  return isNonEmptyString(value) && (value.startsWith("/") || value.startsWith("#"));
}

try {
  const raw = await readFile(copyPath, "utf8");
  const parsed = JSON.parse(raw);
  const errors = [];

  for (const p of requiredPathChecks) {
    assert(isNonEmptyString(getByPath(parsed, p)), `Missing or empty required field: ${p}`, errors);
  }

  assert(isNonEmptyString(parsed.governance_flow?.title), "governance_flow.title is required", errors);
  assert(
    Array.isArray(parsed.governance_flow?.field_items) && parsed.governance_flow.field_items.length >= 1,
    "governance_flow.field_items must contain at least 1 item",
    errors,
  );
  assert(
    Array.isArray(parsed.governance_flow?.lens_items) && parsed.governance_flow.lens_items.length >= 3,
    "governance_flow.lens_items must contain at least 3 items",
    errors,
  );
  const governancePublicText = JSON.stringify(parsed.governance_flow ?? {});
  for (const forbidden of ["사상", "명리", "성경", "Logos", "Field-Lens", "regime_map", "Lens ·"]) {
    assert(
      !governancePublicText.includes(forbidden),
      `governance_flow must not expose internal term on public homepage: ${forbidden}`,
      errors,
    );
  }
  assert(
    parsed.governance_flow?.lens_items?.some((item) => item?.non_gating === true),
    "governance_flow.lens_items must include at least one non_gating auxiliary signal",
    errors,
  );
  assert(
    /^https:\/\//.test(String(parsed.governance_flow?.figjam_url ?? "")),
    "governance_flow.figjam_url must be https",
    errors,
  );

  const maiCard = parsed.hub_links?.mai_profile_card;
  if (maiCard) {
    const maiText = JSON.stringify(maiCard);
    for (const forbidden of ["MBTI", "사상", "명리", "성경", "MAI 성향", "12유형 성향"]) {
      assert(
        !maiText.includes(forbidden),
        `hub_links.mai_profile_card must not expose internal/legacy term: ${forbidden}`,
        errors,
      );
    }
    assert(
      String(maiCard.label ?? "").includes("A·Code 12"),
      "hub_links.mai_profile_card.label must use A·Code 12 public branding",
      errors,
    );
  }

  assert(
    Array.isArray(parsed.why_mkm_ai?.cards) && parsed.why_mkm_ai.cards.length >= 3,
    "why_mkm_ai.cards must contain at least 3 items",
    errors,
  );
  assert(
    Array.isArray(parsed.quick_start?.cards) && parsed.quick_start.cards.length >= 3,
    "quick_start.cards must contain at least 3 items",
    errors,
  );
  assert(
    Array.isArray(parsed.quick_start?.ctas) && parsed.quick_start.ctas.length >= 2,
    "quick_start.ctas must contain at least 2 items",
    errors,
  );
  assert(
    Array.isArray(parsed.home_clinic_flow?.steps) && parsed.home_clinic_flow.steps.length >= 4,
    "home_clinic_flow.steps must contain at least 4 items",
    errors,
  );

  for (const ctaLayout of ["marketing", "workspace"]) {
    const block = parsed.basic_health_chat?.ctas?.[ctaLayout];
    assert(block != null, `basic_health_chat.ctas.${ctaLayout} is required`, errors);
    for (const side of ["primary", "secondary"]) {
      assert(isNonEmptyString(block?.[side]?.label), `basic_health_chat.ctas.${ctaLayout}.${side}.label is required`, errors);
      assert(
        validateLinkTarget(block?.[side]?.href),
        `basic_health_chat.ctas.${ctaLayout}.${side}.href must start with '/' or '#'`,
        errors,
      );
    }
  }

  assert(
    Array.isArray(parsed.hero?.proof_items) && parsed.hero.proof_items.length >= 3,
    "hero.proof_items must contain at least 3 items",
    errors,
  );

  assert(Array.isArray(parsed.hero?.role_cards) && parsed.hero.role_cards.length >= 2, "hero.role_cards must contain at least 2 cards", errors);
  if (Array.isArray(parsed.hero?.role_cards)) {
    parsed.hero.role_cards.forEach((card, idx) => {
      assert(isNonEmptyString(card?.title), `hero.role_cards[${idx}].title is required`, errors);
      assert(isNonEmptyString(card?.body), `hero.role_cards[${idx}].body is required`, errors);
      assert(isNonEmptyString(card?.cta), `hero.role_cards[${idx}].cta is required`, errors);
      assert(validateLinkTarget(card?.href), `hero.role_cards[${idx}].href must start with '/' or '#'`, errors);
      assert(card?.variant === "primary" || card?.variant === "ghost", `hero.role_cards[${idx}].variant must be 'primary' or 'ghost'`, errors);
    });
  }

  assert(Array.isArray(parsed.clinic_o2o?.cards) && parsed.clinic_o2o.cards.length >= 3, "clinic_o2o.cards must contain at least 3 items", errors);
  if (Array.isArray(parsed.clinic_o2o?.cards)) {
    parsed.clinic_o2o.cards.forEach((card, idx) => {
      assert(isNonEmptyString(card?.title), `clinic_o2o.cards[${idx}].title is required`, errors);
      assert(isNonEmptyString(card?.body), `clinic_o2o.cards[${idx}].body is required`, errors);
    });
  }

  assert(Array.isArray(parsed.clinic_o2o?.ctas) && parsed.clinic_o2o.ctas.length >= 3, "clinic_o2o.ctas must contain at least 3 items", errors);
  if (Array.isArray(parsed.clinic_o2o?.ctas)) {
    parsed.clinic_o2o.ctas.forEach((cta, idx) => {
      assert(isNonEmptyString(cta?.label), `clinic_o2o.ctas[${idx}].label is required`, errors);
      assert(validateLinkTarget(cta?.href), `clinic_o2o.ctas[${idx}].href must start with '/' or '#'`, errors);
      assert(cta?.variant === "primary" || cta?.variant === "ghost", `clinic_o2o.ctas[${idx}].variant must be 'primary' or 'ghost'`, errors);
    });
  }

  for (const hubKey of ["lane_governance", "showroom_jemaai", "premium_mkmlife", "b2b_acodeai", "validation_engine"]) {
    const hub = parsed.hub_links?.[hubKey];
    assert(hub != null, `hub_links.${hubKey} is required`, errors);
    assert(
      isNonEmptyString(hub?.href) && /^https:\/\//.test(String(hub.href)),
      `hub_links.${hubKey}.href must be a non-empty https URL`,
      errors,
    );
    assert(isNonEmptyString(hub?.label), `hub_links.${hubKey}.label is required`, errors);
    assert(isNonEmptyString(hub?.sublabel), `hub_links.${hubKey}.sublabel is required`, errors);
  }

  ["consumer", "clinician", "reception", "developer", "contact"].forEach((key) => {
    assert(validateLinkTarget(parsed.links?.[key]), `links.${key} must start with '/' or '#'`, errors);
  });
  if (parsed.links?.enterprise != null) {
    assert(validateLinkTarget(parsed.links.enterprise), "links.enterprise must start with '/' or '#'", errors);
  }

  const ent = parsed.enterprise;
  if (ent != null) {
    for (const p of [
      "seo.title",
      "seo.description",
      "hero.title",
      "hero.subtitle",
      "nav.main_aria_label",
      "nav.principles_aria_label",
      "pillars.title",
      "breadth.title",
      "proof.title",
    ]) {
      assert(isNonEmptyString(getByPath(ent, p)), `enterprise.${p} is required when enterprise block present`, errors);
    }
    assert(Array.isArray(ent.principles) && ent.principles.length >= 3, "enterprise.principles must have >= 3 items", errors);
    assert(Array.isArray(ent.composition?.items) && ent.composition.items.length >= 3, "enterprise.composition.items must have >= 3", errors);
    assert(Array.isArray(ent.pillars?.cards) && ent.pillars.cards.length >= 3, "enterprise.pillars.cards must have >= 3 items", errors);
    assert(isNonEmptyString(ent.contact?.email) && String(ent.contact.email).includes("@"), "enterprise.contact.email required", errors);
    assert(
      String(ent.contact.email).toLowerCase() === "support@mkmlife.com",
      "enterprise.contact.email must be support@mkmlife.com (not clinic footer email)",
      errors,
    );
    for (const fp of ["footer.legal_entity", "footer.brand_line", "footer.rights"]) {
      assert(isNonEmptyString(getByPath(ent, fp)), `enterprise.${fp} is required`, errors);
    }
    assert(
      !String(ent.footer?.rights || "").includes("광명백제한의원"),
      "enterprise.footer.rights must use legal entity (Moksori Network), not clinic name",
      errors,
    );
    assert(Array.isArray(ent.disclaimer?.items) && ent.disclaimer.items.length >= 1, "enterprise.disclaimer.items required", errors);
    const lgBan = ["LG전자", "LG 파트너", "합격", "수상 수상", "파트너십 체결"];
    const blob = JSON.stringify(ent);
    for (const phrase of lgBan) {
      assert(!blob.includes(phrase), `enterprise copy must not include trophy phrase: ${phrase}`, errors);
    }
    for (const banned of ["gmbaekje@naver.com", "광명백제"]) {
      assert(!blob.includes(banned), `enterprise copy must not include ${banned}`, errors);
    }
  }

  const foot = parsed.footer;
  if (foot != null) {
    assert(isNonEmptyString(foot.brand_subline), "footer.brand_subline is required", errors);
    assert(
      !String(foot.company_line || "").includes("광명백제"),
      "footer.company_line must be legal entity (Moksori Network), not clinic name",
      errors,
    );
    assert(
      String(foot.email || "").toLowerCase() === "support@mkmlife.com",
      "footer.email must be support@mkmlife.com",
      errors,
    );
    const footBlob = JSON.stringify(foot);
    for (const banned of ["광명백제", "gmbaekje@naver.com", "140-90-26241"]) {
      assert(!footBlob.includes(banned), `footer must not include clinic-only field: ${banned}`, errors);
    }
  }

  if (errors.length > 0) {
    console.error("[check-public-copy-schema] validation failed.");
    for (const error of errors) console.error(`- ${error}`);
    process.exitCode = 1;
  } else {
    console.log("[check-public-copy-schema] passed.");
  }
} catch (error) {
  console.error("[check-public-copy-schema] failed.");
  if (error instanceof Error && error.message) console.error(error.message);
  process.exitCode = 1;
}
