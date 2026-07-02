"use client";

import { useCallback, useEffect, useState } from "react";

import { logosResearchCopy } from "@/content/logosResearchCopy";

type QuotaPayload = {
  remaining?: number;
  total?: number;
  payment_ui_enabled?: boolean;
  payment_status?: string;
  feedback_issues_url?: string;
};

export function LogosResearchAskQuotaBar({
  refreshKey = 0,
  onRemaining,
}: {
  refreshKey?: number;
  onRemaining?: (remaining: number | null) => void;
}) {
  const [quota, setQuota] = useState<QuotaPayload | null>(null);
  const studio = "studio" in logosResearchCopy ? logosResearchCopy.studio : null;
  const beta =
    "inquiry_beta" in logosResearchCopy && logosResearchCopy.inquiry_beta
      ? logosResearchCopy.inquiry_beta
      : null;

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/logos-research/quota", { cache: "no-store" });
      if (!res.ok) return;
      const data = (await res.json()) as QuotaPayload;
      setQuota(data);
      onRemaining?.(typeof data.remaining === "number" ? data.remaining : null);
    } catch {
      /* non-fatal */
    }
  }, [onRemaining]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  if (!quota || quota.remaining == null || quota.total == null) return null;

  const issuesUrl =
    quota.feedback_issues_url ||
    (beta && typeof beta === "object" && "github_issues" in beta
      ? String((beta as { github_issues?: string }).github_issues || "")
      : "");

  return (
    <div className="lr-ask-quota-bar" role="status" aria-live="polite">
      <span>
        {studio?.quota_remaining ?? "오늘 남은 무료 쿼터"}{" "}
        <strong>
          {quota.remaining}
        </strong>{" "}
        / {quota.total}
      </span>
      {quota.payment_status === "deferred_post_oss_verification" ? (
        <span className="lr-ask-muted lr-ask-quota-note">
          결제·Pro SKU — OSS 공개·검증 후 연결 예정
        </span>
      ) : null}
      {issuesUrl ? (
        <a className="lr-ask-quota-feedback" href={issuesUrl} target="_blank" rel="noopener noreferrer">
          {beta && typeof beta === "object" && "feedback_cta" in beta
            ? String((beta as { feedback_cta?: string }).feedback_cta || "GitHub 피드백")
            : "GitHub 피드백"}
        </a>
      ) : null}
    </div>
  );
}
