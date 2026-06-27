"use client";

import type { PasteExtractDraftV1 } from "@/lib/clinician-chart-paste-extract-v1";

export async function fetchPasteExtractDraftLlmV1(
  chartText: string,
  clinicianEmail?: string,
): Promise<{ ok: true; draft: PasteExtractDraftV1; provider?: string } | { ok: false; error: string }> {
  const res = await fetch("/api/clinician/paste-extract-v1", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...(clinicianEmail ? { "x-clinician-email": clinicianEmail } : {}),
    },
    body: JSON.stringify({ chart_text: chartText }),
  });
  const data = (await res.json()) as {
    success?: boolean;
    draft?: PasteExtractDraftV1;
    provider?: string;
    error?: string;
  };
  if (!res.ok || !data.success || !data.draft) {
    return { ok: false, error: data.error || `http_${res.status}` };
  }
  return { ok: true, draft: data.draft, provider: data.provider };
}

export function pasteExtractLlmClientEnabled(): boolean {
  const pub = (process.env.NEXT_PUBLIC_KM_CLINICIAN_PASTE_EXTRACT_LLM || "").trim().toLowerCase();
  return pub === "1" || pub === "true" || pub === "yes" || pub === "on";
}
