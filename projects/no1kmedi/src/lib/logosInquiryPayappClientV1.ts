/** Logos inquiry Pro checkout — server-side billing checkout (no client keys). */

export type BillingCheckoutResult = {
  success: boolean;
  order_id?: string;
  redirect_url?: string;
  error?: string;
  dry_run_keys?: boolean;
  note_ko?: string;
  g12_human_inject?: boolean;
};

export async function startLogosProCheckout(email: string): Promise<BillingCheckoutResult> {
  const res = await fetch("/api/logos-research/billing/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim() }),
  });
  const data = (await res.json()) as BillingCheckoutResult;
  if (!res.ok || !data.success) {
    return {
      success: false,
      error: data.error || `checkout_http_${res.status}`,
      g12_human_inject: data.g12_human_inject,
    };
  }
  return data;
}
