"use client";

import { useState } from "react";
import { siteCopy } from "@/content/siteCopy";
import type { CompressionPilotAuditApplyPayload } from "@/lib/compressionPilotAuditApplyV1";
import { isTurnstileClientEnabled } from "@/lib/turnstileConfigV1";
import { TurnstileField } from "@/components/TurnstileField";

type ApplyCopy = NonNullable<(typeof siteCopy)["compression_pilot_audit_apply"]>;

type ApiResponse = {
  success: boolean;
  application_id?: string;
  error?: string;
};

function SelectField({
  label,
  value,
  onChange,
  options,
  required = true,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  required?: boolean;
}) {
  return (
    <label>
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} required={required}>
        <option value="">선택</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function CompressionPilotAuditApplyForm({ copy }: { copy: ApplyCopy }) {
  const [companyLegalName, setCompanyLegalName] = useState("");
  const [website, setWebsite] = useState("");
  const [country, setCountry] = useState("대한민국");
  const [companyStage, setCompanyStage] = useState("");
  const [teamSize, setTeamSize] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactRole, setContactRole] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [primaryDomain, setPrimaryDomain] = useState("");
  const [llmProvider, setLlmProvider] = useState("");
  const [monthlyTokenVolume, setMonthlyTokenVolume] = useState("");
  const [useCaseSummary, setUseCaseSummary] = useState("");
  const [maskedJsonlReadiness, setMaskedJsonlReadiness] = useState("");
  const [estimatedSampleRows, setEstimatedSampleRows] = useState("");
  const [referralSource, setReferralSource] = useState("");
  const [piiScrubAck, setPiiScrubAck] = useState(false);
  const [ndaAck, setNdaAck] = useState(false);
  const [notSlaAck, setNotSlaAck] = useState(false);
  const [noGuaranteeAck, setNoGuaranteeAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [turnstileToken, setTurnstileToken] = useState("");
  const turnstileEnabled = isTurnstileClientEnabled();

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!piiScrubAck || !ndaAck || !notSlaAck || !noGuaranteeAck) {
      setError(copy.errors.ack_required);
      return;
    }
    if (turnstileEnabled && !turnstileToken.trim()) {
      setError("보안 확인을 완료해 주세요.");
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    setApplicationId("");

    const payload: CompressionPilotAuditApplyPayload = {
      company_legal_name: companyLegalName,
      website,
      country,
      company_stage: companyStage,
      team_size: teamSize || undefined,
      contact_name: contactName,
      contact_email: contactEmail,
      contact_role: contactRole,
      contact_phone: contactPhone || undefined,
      primary_domain: primaryDomain,
      llm_provider: llmProvider,
      monthly_token_volume: monthlyTokenVolume,
      use_case_summary: useCaseSummary,
      masked_jsonl_readiness: maskedJsonlReadiness,
      estimated_sample_rows: estimatedSampleRows,
      referral_source: referralSource || undefined,
      pii_scrub_ack: piiScrubAck,
      nda_ack: ndaAck,
      not_sla_ack: notSlaAck,
      no_guarantee_ack: noGuaranteeAck,
      turnstile_token: turnstileEnabled ? turnstileToken : undefined,
    };

    try {
      const res = await fetch("/api/leads/compression-pilot-audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = (await res.json()) as ApiResponse;
      if (!res.ok || !json.success) {
        setError(json.error || copy.errors.save_failed);
        return;
      }
      setStatus(copy.success);
      if (json.application_id) setApplicationId(json.application_id);
    } catch {
      setError(copy.errors.network);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="enterprise-apply-form" onSubmit={onSubmit}>
      <fieldset className="enterprise-apply-fieldset">
        <legend>{copy.sections.organization}</legend>
        <label>
          {copy.labels.company_legal_name}
          <input value={companyLegalName} onChange={(e) => setCompanyLegalName(e.target.value)} required />
        </label>
        <label>
          {copy.labels.website}
          <input
            type="url"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder={copy.placeholders.website}
          />
        </label>
        <label>
          {copy.labels.country}
          <input
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            placeholder={copy.placeholders.country}
            required
          />
        </label>
        <SelectField
          label={copy.labels.company_stage}
          value={companyStage}
          onChange={setCompanyStage}
          options={copy.options.company_stage}
        />
        <SelectField
          label={copy.labels.team_size}
          value={teamSize}
          onChange={setTeamSize}
          options={copy.options.team_size}
          required={false}
        />
      </fieldset>

      <fieldset className="enterprise-apply-fieldset">
        <legend>{copy.sections.contact}</legend>
        <label>
          {copy.labels.contact_name}
          <input value={contactName} onChange={(e) => setContactName(e.target.value)} required />
        </label>
        <label>
          {copy.labels.contact_email}
          <input type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} required />
        </label>
        <label>
          {copy.labels.contact_role}
          <input value={contactRole} onChange={(e) => setContactRole(e.target.value)} required />
        </label>
        <label>
          {copy.labels.contact_phone}
          <input type="tel" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} />
        </label>
      </fieldset>

      <fieldset className="enterprise-apply-fieldset">
        <legend>{copy.sections.use_case}</legend>
        <SelectField
          label={copy.labels.primary_domain}
          value={primaryDomain}
          onChange={setPrimaryDomain}
          options={copy.options.primary_domain}
        />
        <SelectField
          label={copy.labels.llm_provider}
          value={llmProvider}
          onChange={setLlmProvider}
          options={copy.options.llm_provider}
        />
        <SelectField
          label={copy.labels.monthly_token_volume}
          value={monthlyTokenVolume}
          onChange={setMonthlyTokenVolume}
          options={copy.options.monthly_token_volume}
        />
        <label className="enterprise-apply-full">
          {copy.labels.use_case_summary}
          <textarea
            value={useCaseSummary}
            onChange={(e) => setUseCaseSummary(e.target.value)}
            placeholder={copy.placeholders.use_case_summary}
            rows={4}
            minLength={20}
            required
          />
        </label>
      </fieldset>

      <fieldset className="enterprise-apply-fieldset">
        <legend>{copy.sections.data}</legend>
        <SelectField
          label={copy.labels.masked_jsonl_readiness}
          value={maskedJsonlReadiness}
          onChange={setMaskedJsonlReadiness}
          options={copy.options.masked_jsonl_readiness}
        />
        <SelectField
          label={copy.labels.estimated_sample_rows}
          value={estimatedSampleRows}
          onChange={setEstimatedSampleRows}
          options={copy.options.estimated_sample_rows}
        />
        <label className="enterprise-apply-full">
          {copy.labels.referral_source}
          <input
            value={referralSource}
            onChange={(e) => setReferralSource(e.target.value)}
            placeholder={copy.placeholders.referral_source}
          />
        </label>
      </fieldset>

      <fieldset className="enterprise-apply-fieldset enterprise-apply-ack">
        <legend>{copy.sections.ack}</legend>
        <label className="enterprise-apply-check">
          <input type="checkbox" checked={piiScrubAck} onChange={(e) => setPiiScrubAck(e.target.checked)} />
          {copy.labels.pii_scrub_ack}
        </label>
        <label className="enterprise-apply-check">
          <input type="checkbox" checked={ndaAck} onChange={(e) => setNdaAck(e.target.checked)} />
          {copy.labels.nda_ack}
        </label>
        <label className="enterprise-apply-check">
          <input type="checkbox" checked={notSlaAck} onChange={(e) => setNotSlaAck(e.target.checked)} />
          {copy.labels.not_sla_ack}
        </label>
        <label className="enterprise-apply-check">
          <input type="checkbox" checked={noGuaranteeAck} onChange={(e) => setNoGuaranteeAck(e.target.checked)} />
          {copy.labels.no_guarantee_ack}
        </label>
      </fieldset>

      {turnstileEnabled ? (
        <TurnstileField
          onToken={setTurnstileToken}
          onExpire={() => setTurnstileToken("")}
          onError={() => setTurnstileToken("")}
        />
      ) : null}

      <button type="submit" className="btn btn-primary enterprise-btn-primary" disabled={busy}>
        {busy ? copy.submit_busy : copy.submit_idle}
      </button>

      {applicationId ? (
        <p className="enterprise-apply-id">
          신청 ID: <code>{applicationId}</code>
        </p>
      ) : null}
      {status ? <p className="lead-success">{status}</p> : null}
      {error ? <p className="consult-error">{error}</p> : null}
    </form>
  );
}
