export type CompressionPilotAuditApplyPayload = {
  company_legal_name: string;
  website?: string;
  country: string;
  company_stage: string;
  team_size?: string;
  contact_name: string;
  contact_email: string;
  contact_role: string;
  contact_phone?: string;
  primary_domain: string;
  llm_provider: string;
  monthly_token_volume: string;
  use_case_summary: string;
  masked_jsonl_readiness: string;
  estimated_sample_rows: string;
  referral_source?: string;
  pii_scrub_ack: boolean;
  nda_ack: boolean;
  not_sla_ack: boolean;
  no_guarantee_ack: boolean;
  turnstile_token?: string;
};

const REQUIRED_STRINGS: (keyof CompressionPilotAuditApplyPayload)[] = [
  "company_legal_name",
  "country",
  "company_stage",
  "contact_name",
  "contact_email",
  "contact_role",
  "primary_domain",
  "llm_provider",
  "monthly_token_volume",
  "use_case_summary",
  "masked_jsonl_readiness",
  "estimated_sample_rows",
];

export function validateCompressionPilotAuditApply(
  body: Partial<CompressionPilotAuditApplyPayload>,
): string | null {
  for (const key of REQUIRED_STRINGS) {
    const val = body[key];
    if (typeof val !== "string" || !val.trim()) return `${key}_required`;
  }
  if (!body.contact_email?.includes("@")) return "contact_email_invalid";
  if (!body.pii_scrub_ack) return "pii_scrub_ack_required";
  if (!body.nda_ack) return "nda_ack_required";
  if (!body.not_sla_ack) return "not_sla_ack_required";
  if (!body.no_guarantee_ack) return "no_guarantee_ack_required";
  if ((body.use_case_summary?.trim().length ?? 0) < 20) return "use_case_summary_too_short";
  return null;
}

export function normalizeCompressionPilotAuditApply(
  body: CompressionPilotAuditApplyPayload,
  applicationId: string,
) {
  return {
    schema: "compression_pilot_audit_apply_v1",
    application_id: applicationId,
    ts_utc: new Date().toISOString(),
    source: "jema-ai-enterprise-apply",
    send_gate: "HOLD",
    program: "tier_0_free_masked_jsonl_audit",
    company_legal_name: body.company_legal_name.trim(),
    website: (body.website || "").trim(),
    country: body.country.trim(),
    company_stage: body.company_stage,
    team_size: body.team_size || "",
    contact_name: body.contact_name.trim(),
    contact_email: body.contact_email.trim().toLowerCase(),
    contact_role: body.contact_role.trim(),
    contact_phone: (body.contact_phone || "").trim(),
    primary_domain: body.primary_domain,
    llm_provider: body.llm_provider,
    monthly_token_volume: body.monthly_token_volume,
    use_case_summary: body.use_case_summary.trim(),
    masked_jsonl_readiness: body.masked_jsonl_readiness,
    estimated_sample_rows: body.estimated_sample_rows,
    referral_source: (body.referral_source || "").trim(),
    acknowledgements: {
      pii_scrub_ack: true,
      nda_ack: true,
      not_sla_ack: true,
      no_guarantee_ack: true,
    },
  };
}
