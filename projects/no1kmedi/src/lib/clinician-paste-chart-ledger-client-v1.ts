import type { EightChannelAuditV1 } from "@/lib/clinician-paste-chart-eight-channel-audit-v1";
import type { EncounterSessionEnvelopeV1 } from "@/lib/clinician-encounter-session-envelope-v1";

export type PasteChartLedgerAppendClientInput = {
  slug?: string;
  display_label?: string;
  ephemeral?: boolean;
  request_id?: string;
  session_envelope: EncounterSessionEnvelopeV1;
  eight_channel_audit_v1?: EightChannelAuditV1;
  patient_care_bundle?: Record<string, unknown>;
};

export type PasteChartLedgerAppendClientResult =
  | { ok: true; ledger?: string }
  | { ok: false; error: string };

function clinicianHeaders(email?: string): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  const e = email?.trim().toLowerCase();
  if (e) h["x-clinician-email"] = e;
  return h;
}

/**
 * Fire-and-forget safe: callers should not block SOAP UI on ledger failure.
 */
export async function appendPasteChartEncounterLedger(
  input: PasteChartLedgerAppendClientInput,
  clinicianEmail?: string,
): Promise<PasteChartLedgerAppendClientResult> {
  try {
    const res = await fetch("/api/clinician/paste-chart-ledger-append-v1", {
      method: "POST",
      headers: clinicianHeaders(clinicianEmail),
      body: JSON.stringify({
        slug: input.slug,
        display_label: input.display_label,
        ephemeral: input.ephemeral,
        request_id: input.request_id,
        session_envelope: input.session_envelope,
        eight_channel_audit_v1: input.eight_channel_audit_v1,
        patient_care_bundle: input.patient_care_bundle,
        source: "gold_panel_v1",
      }),
    });
    const json = (await res.json()) as { success?: boolean; error?: string; ledger?: string };
    if (!res.ok || !json.success) {
      return { ok: false, error: json.error || `http_${res.status}` };
    }
    return { ok: true, ledger: json.ledger };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}
