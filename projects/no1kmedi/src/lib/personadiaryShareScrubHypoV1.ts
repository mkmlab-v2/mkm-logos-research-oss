const MAX_TEXT = 2000;

const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
const PHONE_RE = /(?<!\d)(?:\+?82[-.\s]?)?0?1[0-9][-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)/g;
const PAY_URL_RE = /https?:\/\/[^\s]*(?:pay|payment|checkout|mkmlife)[^\s]*/gi;
const CARD_RE = /\b(?:\d[ -]*?){13,19}\b/g;

export type ShareScrubResult = {
  text: string;
  scrubbed: boolean;
};

/** M1 rule scrub — local-only; mirrors scripts/personadiary_share_scrub_hypo_v1.py */
export function scrubShareTextHypoV1(text: string): ShareScrubResult {
  const original = text.trim();
  let out = original;
  if (out.length > MAX_TEXT) out = out.slice(0, MAX_TEXT);
  out = out.replace(EMAIL_RE, "[redacted-email]");
  out = out.replace(PAY_URL_RE, "[redacted-pay-url]");
  out = out.replace(CARD_RE, "[redacted-card]");
  out = out.replace(PHONE_RE, "[redacted-phone]");
  out = out.replace(/\s+/g, " ").trim();
  return { text: out, scrubbed: out !== original || original.length > MAX_TEXT };
}

export const SHARE_SCRUB_BOUNDARY_ACK =
  "research_only · no mkmlife payment merge · copy gate before export";
