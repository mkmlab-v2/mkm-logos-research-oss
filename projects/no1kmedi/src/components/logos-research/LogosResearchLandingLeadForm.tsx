"use client";

import { useCallback, useState } from "react";

type LeadState = "idle" | "submitting" | "ok" | "error";

type Props = {
  cta: string;
  placeholderEmail: string;
  placeholderOrg: string;
  placeholderNote: string;
  labelSending: string;
  mailFallbackHref: string;
  mailFallbackLabel: string;
};

export function LogosResearchLandingLeadForm({
  cta,
  placeholderEmail,
  placeholderOrg,
  placeholderNote,
  labelSending,
  mailFallbackHref,
  mailFallbackLabel,
}: Props) {
  const [email, setEmail] = useState("");
  const [organization, setOrganization] = useState("");
  const [note, setNote] = useState("");
  const [state, setState] = useState<LeadState>("idle");
  const [message, setMessage] = useState("");

  const submit = useCallback(async () => {
    setState("submitting");
    setMessage("");
    try {
      const res = await fetch("/api/logos-research/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          organization,
          note,
          tier: "pilot",
          source: "logos-research-landing-v1",
        }),
      });
      const data = (await res.json()) as { ok?: boolean; lead_id?: string; error?: string };
      if (!res.ok || !data.ok) throw new Error(data.error || "lead_failed");
      setState("ok");
      setMessage(data.lead_id || "submitted");
    } catch (error: unknown) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "lead_failed");
    }
  }, [email, note, organization]);

  return (
    <div className="lr-landing-lead">
      <div className="lr-studio-form lr-studio-form--grid">
        <input
          className="lr-studio-input"
          type="email"
          placeholder={placeholderEmail}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
        />
        <input
          className="lr-studio-input"
          type="text"
          placeholder={placeholderOrg}
          value={organization}
          onChange={(e) => setOrganization(e.target.value)}
        />
        <textarea
          className="lr-studio-textarea"
          rows={2}
          placeholder={placeholderNote}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <button
          type="button"
          className="lr-btn lr-btn-primary"
          disabled={state === "submitting" || !email.includes("@")}
          onClick={submit}
        >
          {state === "submitting" ? labelSending : cta}
        </button>
        {message ? <p className="lr-studio-lead-msg">{message}</p> : null}
      </div>
      <div className="lr-hero-cta lr-landing-lead__alt">
        <a className="lr-btn lr-btn-ghost" href={mailFallbackHref}>
          {mailFallbackLabel}
        </a>
      </div>
    </div>
  );
}
