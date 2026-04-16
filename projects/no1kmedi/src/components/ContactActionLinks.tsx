/**
 * @MKM12-METADATA
 * Type: UI
 * Vector: {S:0.70, L:0.48, K:0.76, M:0.34}
 * Balance: 89
 * Purpose: Track contact CTA interactions for conversion funnel.
 * Keywords: React, CTA, analytics, book_call, conversion
 */
"use client";

import { useEffect } from "react";

function trackEvent(event: string, payload?: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  const w = window as Window & { dataLayer?: Array<Record<string, unknown>> };
  if (Array.isArray(w.dataLayer)) {
    w.dataLayer.push({ event, ...payload });
  }
}

type ContactActionLinksProps = {
  email: string;
  label: string;
};

export function ContactActionLinks({ email, label }: ContactActionLinksProps) {
  useEffect(() => {
    trackEvent("view_pricing", { location: "contact_section" });
  }, []);

  return (
    <p>
      {label}:{" "}
      <a
        href={`mailto:${email}?subject=%5BCompany%5D%20book%20intro%20call`}
        onClick={() => trackEvent("book_call", { channel: "mailto_contact" })}
      >
        {email}
      </a>
    </p>
  );
}
