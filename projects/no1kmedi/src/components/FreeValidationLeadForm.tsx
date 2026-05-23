/**
 * @MKM12-METADATA
 * Type: UI
 * Vector: {S:0.72, L:0.62, K:0.78, M:0.44}
 * Balance: 90
 * Purpose: Capture free validation leads and emit funnel events.
 * Keywords: React, lead, form, analytics, conversion
 */
"use client";

import { useState } from "react";
import { siteCopy } from "@/content/siteCopy";

type LeadPayload = {
  name: string;
  email: string;
  company: string;
  use_case: string;
};

type LeadApiResponse = {
  success: boolean;
  lead_id?: string;
  error?: string;
};

function trackEvent(event: string, payload?: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  const w = window as Window & { dataLayer?: Array<Record<string, unknown>> };
  if (Array.isArray(w.dataLayer)) {
    w.dataLayer.push({ event, ...payload });
  }
}

export function FreeValidationLeadForm() {
  const copy = siteCopy.free_validation_lead;
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [useCase, setUseCase] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !email.trim() || !company.trim()) {
      setError(copy.errors.required_fields);
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");

    const payload: LeadPayload = {
      name: name.trim(),
      email: email.trim().toLowerCase(),
      company: company.trim(),
      use_case: useCase.trim(),
    };

    try {
      const res = await fetch("/api/leads/free-validation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const json = (await res.json()) as LeadApiResponse;
      if (!res.ok || !json.success) {
        setError(json.error || copy.errors.save_failed);
        return;
      }

      trackEvent("submit_lead", { lead_channel: "free_validation_form" });
      setStatus(copy.success);
      setName("");
      setEmail("");
      setCompany("");
      setUseCase("");
    } catch {
      setError(copy.errors.network);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card lead-form-card">
      <h3>{copy.title}</h3>
      <p className="section-lead">{copy.section_lead}</p>
      <form className="lead-form" onSubmit={onSubmit}>
        <label>
          {copy.labels.name}
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          {copy.labels.email}
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          {copy.labels.company}
          <input value={company} onChange={(e) => setCompany(e.target.value)} required />
        </label>
        <label>
          {copy.labels.use_case}
          <input
            value={useCase}
            onChange={(e) => setUseCase(e.target.value)}
            placeholder={copy.placeholders.use_case}
          />
        </label>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={busy}
          onClick={() => trackEvent("click_free_validation", { location: "home_contact" })}
        >
          {busy ? copy.submit_busy : copy.submit_idle}
        </button>
      </form>
      {status ? <p className="lead-success">{status}</p> : null}
      {error ? <p className="consult-error">{error}</p> : null}
    </div>
  );
}
