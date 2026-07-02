import { NextRequest, NextResponse } from "next/server";

import {
  isLogosInquiryPaymentEnabled,
  LOGOS_INQUIRY_BETA_DEFAULTS,
} from "@/lib/logosInquiryBetaV1";
import { hasLogosProAccess, resolveLogosAccess } from "@/lib/logosResearchAccessV1";
import {
  isLogosStudioQuotaDisabled,
  LOGOS_FREE_DAILY_QUOTA,
  quotaRemaining,
  readQuotaState,
} from "@/lib/logosResearchQuotaV1";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const access = await resolveLogosAccess(request, "logos.query.read");
  const pro = hasLogosProAccess(access);
  const quotaOff = isLogosStudioQuotaDisabled();
  const state = readQuotaState(request);
  const paymentEnabled = isLogosInquiryPaymentEnabled();

  return NextResponse.json(
    {
      schema: "logos_inquiry_quota_v1",
      remaining: quotaRemaining(state, pro || quotaOff),
      total: LOGOS_FREE_DAILY_QUOTA,
      pro,
      quota_disabled: quotaOff,
      payment_ui_enabled: paymentEnabled,
      payment_status: paymentEnabled
        ? "enabled"
        : LOGOS_INQUIRY_BETA_DEFAULTS.payment_status,
      feedback_issues_url: LOGOS_INQUIRY_BETA_DEFAULTS.feedback_issues_url,
      oss_repo_url: LOGOS_INQUIRY_BETA_DEFAULTS.oss_repo_url,
      send_gate: "HOLD",
      research_only: true,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
