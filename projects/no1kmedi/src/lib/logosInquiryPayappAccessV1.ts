import type { NextRequest } from "next/server";

import { getPayments } from "@/app/api/payment/payapp/_store";

export const LOGOS_BILLING_EMAIL_COOKIE = "lr_billing_email_v1";

const LOGOS_INQUIRY_PLAN_PREFIX = "logos_inquiry_";

export function logosBillingEmailFromRequest(request: NextRequest): string {
  const header = (request.headers.get("x-logos-billing-email") || "").trim().toLowerCase();
  if (header) return header;
  return (request.cookies.get(LOGOS_BILLING_EMAIL_COOKIE)?.value || "").trim().toLowerCase();
}

export async function hasPaidLogosInquiryPlan(emailRaw: string): Promise<boolean> {
  const email = emailRaw.trim().toLowerCase();
  if (!email) return false;
  const rows = await getPayments();
  return rows.some(
    (row) =>
      row.email.toLowerCase() === email &&
      row.state === "paid" &&
      (row.plan_code || "").startsWith(LOGOS_INQUIRY_PLAN_PREFIX),
  );
}
