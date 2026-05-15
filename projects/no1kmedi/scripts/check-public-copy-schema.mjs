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
  "links.consumer",
  "links.clinician",
  "links.reception",
  "links.contact",
  "hero.eyebrow",
  "hero.title",
  "hero.subtitle",
  "hero.cta_primary",
  "hero.cta_secondary",
  "hero.cta_tertiary",
  "hero.cta_quaternary",
  "trust.note",
  "public_solution.title",
  "public_solution.section_lead",
  "clinic_o2o.title",
  "clinic_o2o.section_lead",
  "landing_flow.title",
  "contact.title",
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

  for (const hubKey of ["showroom_jemaai", "premium_mkmlife", "b2b_acodeai"]) {
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

  ["consumer", "clinician", "reception", "contact"].forEach((key) => {
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
