/** Logos inquiry public beta flags — payment deferred until post-OSS verification. */

export type LogosInquiryBetaStatus = {
  payment_ui_enabled: boolean;
  payment_status: "deferred_post_oss_verification" | "enabled";
  free_daily_quota: number;
  feedback_issues_url: string;
  oss_repo_url: string;
};

function isTruthyEnv(value: string | undefined): boolean {
  if (!value) return false;
  const v = value.trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

/** Server + client: payment/checkout hidden unless explicitly enabled (post-OSS). */
export function isLogosInquiryPaymentEnabled(): boolean {
  return isTruthyEnv(process.env.LOGOS_INQUIRY_PAYMENT_ENABLED)
    || isTruthyEnv(process.env.NEXT_PUBLIC_LOGOS_INQUIRY_PAYMENT_ENABLED);
}

export const LOGOS_INQUIRY_BETA_DEFAULTS: LogosInquiryBetaStatus = {
  payment_ui_enabled: false,
  payment_status: "deferred_post_oss_verification",
  free_daily_quota: 8,
  feedback_issues_url: "https://github.com/mkmlab-v2/mkm-logos-research-oss/issues",
  oss_repo_url: "https://github.com/mkmlab-v2/mkm-logos-research-oss",
};
