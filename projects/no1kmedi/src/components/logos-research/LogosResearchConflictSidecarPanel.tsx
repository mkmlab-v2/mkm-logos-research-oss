"use client";

import { useState } from "react";
import { useEffect } from "react";

import type { ConflictContextResult } from "@/lib/logosStudioConflictBridgeV1";

type SchoolRow = {
  school_tier?: string;
  interpretation_ko?: string;
  citation_lock_anchors?: string[];
  verse_refs?: string[];
  traditions?: string[];
  labels?: string[];
};

type ConflictGroup = {
  conflict_group_id?: string;
  lexicon_base?: string;
  school_count?: number;
  schools?: SchoolRow[];
  retrieval_score?: number;
};

type Props = {
  context: Extract<ConflictContextResult, { ok: true }>;
};

export function LogosResearchConflictSidecarPanel({ context }: Props) {
  const [feedbackState, setFeedbackState] = useState<"idle" | "sending" | "ok" | "error">("idle");
  const [feedbackMsg, setFeedbackMsg] = useState("");
  const [issueType, setIssueType] = useState<"translation" | "context" | "source" | "other">(
    "context",
  );
  const [feedbackSummary, setFeedbackSummary] = useState<{
    up?: number;
    down?: number;
    agreement_rate?: number;
    agreement_rate_7d?: number;
    agreement_rate_30d?: number;
    down_rate_7d?: number;
    down_rate_30d?: number;
    top_issue_types?: Record<string, number>;
    top_anchors?: Array<{ evidence_anchor?: string; total?: number; down?: number }>;
  } | null>(null);
  const visibleGroups = context.groups || [];

  const title =
    context.ui_contract?.panel_title_ko ?? "학파별 해석 격벽 (BigSet · query-time)";
  const disclaimer =
    context.ui_contract?.disclaimer_ko ??
    "[HYPO] 질문과 매칭된 conflict surface만 표시 — 단정·NON_GATING 아님.";
  const firstAnchor =
    visibleGroups[0]?.schools?.[0]?.citation_lock_anchors?.[0] ||
    visibleGroups[0]?.schools?.[0]?.verse_refs?.[0] ||
    "";

  async function sendFeedback(verdict: "up" | "down") {
    setFeedbackState("sending");
    setFeedbackMsg("");
    try {
      const res = await fetch("/api/logos-research/evidence-feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          verdict,
          issue_type: verdict === "down" ? issueType : "",
          preset_id: context.preset_id || "",
          query: context.query || "",
          evidence_anchor: firstAnchor,
          note: `match_mode=${context.match_mode || "none"}`,
        }),
      });
      const data = (await res.json()) as { ok?: boolean; error?: string };
      if (!res.ok || !data.ok) throw new Error(data.error || "feedback_failed");
      setFeedbackState("ok");
      setFeedbackMsg("검증 피드백이 반영되었습니다.");
    } catch (e: unknown) {
      setFeedbackState("error");
      setFeedbackMsg(e instanceof Error ? e.message : "feedback_failed");
    }
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/telemetry/summary", { cache: "no-store" });
        if (!res.ok) return;
        const data = (await res.json()) as {
          logos_studio_feedback?: {
            counts?: { up?: number; down?: number };
            ratios?: { agreement_rate?: number };
            top_issue_types?: Record<string, number>;
            top_anchors?: Array<{ evidence_anchor?: string; total?: number; down?: number }>;
            windows?: {
              w7?: { ratios?: { agreement_rate?: number; down_rate?: number } };
              w30?: { ratios?: { agreement_rate?: number; down_rate?: number } };
            };
          } | null;
        };
        if (cancelled) return;
        const fs = data.logos_studio_feedback;
        if (!fs) return;
        setFeedbackSummary({
          up: fs.counts?.up ?? 0,
          down: fs.counts?.down ?? 0,
          agreement_rate: fs.ratios?.agreement_rate ?? 0,
          agreement_rate_7d: fs.windows?.w7?.ratios?.agreement_rate ?? 0,
          agreement_rate_30d: fs.windows?.w30?.ratios?.agreement_rate ?? 0,
          down_rate_7d: fs.windows?.w7?.ratios?.down_rate ?? 0,
          down_rate_30d: fs.windows?.w30?.ratios?.down_rate ?? 0,
          top_issue_types: fs.top_issue_types ?? {},
          top_anchors: fs.top_anchors ?? [],
        });
      } catch {
        // summary badge is optional
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!visibleGroups.length) return null;
  const totalVotes = (feedbackSummary?.up ?? 0) + (feedbackSummary?.down ?? 0);
  const downRate = totalVotes > 0 ? (feedbackSummary?.down ?? 0) / totalVotes : 0;
  const downRate7d = feedbackSummary?.down_rate_7d ?? 0;
  const downRate30d = feedbackSummary?.down_rate_30d ?? 0;
  const worseningDelta = downRate7d - downRate30d;
  const showRiskWarn =
    (totalVotes >= 5 && downRate >= 0.35) || (downRate7d >= 0.25 && worseningDelta >= 0.12);

  return (
    <div className="lr-studio-lattice lr-studio-conflict-sidecar" aria-labelledby="lr-conflict-sidecar-title">
      <h3 id="lr-conflict-sidecar-title">{title}</h3>
      <p className="lr-studio-lattice-lead">
        {disclaimer}
        {context.match_mode ? ` · match: ${context.match_mode}` : ""}
      </p>
      {visibleGroups.map((group) => (
        <div key={group.conflict_group_id} className="lr-studio-conflict-group">
          <h4>
            {group.lexicon_base || group.conflict_group_id}
            {group.school_count != null ? (
              <span className="lr-studio-conflict-meta"> · {group.school_count} schools</span>
            ) : null}
            {group.retrieval_score != null ? (
              <span className="lr-studio-conflict-meta"> · score {group.retrieval_score}</span>
            ) : null}
          </h4>
          <ul className="lr-studio-conflict-schools">
            {(group.schools || []).map((school) => (
              <li key={`${group.conflict_group_id}-${school.school_tier}`}>
                <strong>{school.school_tier}</strong>
                {school.traditions?.length ? (
                  <span className="lr-studio-conflict-meta"> [{school.traditions.join(", ")}]</span>
                ) : null}
                {school.interpretation_ko ? (
                  <p className="lr-studio-conflict-interp">{school.interpretation_ko}</p>
                ) : null}
                {school.verse_refs?.length ? (
                  <p className="lr-studio-verse-anchors">구절: {school.verse_refs.join(" · ")}</p>
                ) : null}
                {school.citation_lock_anchors?.length ? (
                  <ul className="lr-studio-conflict-anchors">
                    {school.citation_lock_anchors.slice(0, 4).map((url) => (
                      <li key={url}>
                        <a href={url} rel="noopener noreferrer">
                          {url}
                        </a>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ))}
      <div className="lr-studio-evidence-feedback">
        {feedbackSummary ? (
          <p className="lr-studio-evidence-feedback-summary" role="status">
            최근 검증 👍 {feedbackSummary.up ?? 0} · 👎 {feedbackSummary.down ?? 0} · 일치율{" "}
            {Math.round((feedbackSummary.agreement_rate ?? 0) * 100)}% (7d{" "}
            {Math.round((feedbackSummary.agreement_rate_7d ?? 0) * 100)} / 30d{" "}
            {Math.round((feedbackSummary.agreement_rate_30d ?? 0) * 100)})
          </p>
        ) : null}
        {showRiskWarn ? (
          <p className="lr-studio-evidence-risk-warn" role="alert">
            주의 필요: 최근 이슈 비율이 높거나 악화 추세입니다 (현재 👎 {Math.round(downRate * 100)}%
            {worseningDelta > 0
              ? ` · 7d 대비 30d 악화 +${Math.round(worseningDelta * 100)}%p`
              : ""}).
          </p>
        ) : null}
        <p className="lr-studio-evidence-feedback-label">이 증거가 타당한가요?</p>
        <div className="lr-studio-evidence-feedback-actions">
          <button
            type="button"
            className="lr-studio-evidence-feedback-btn"
            disabled={feedbackState === "sending"}
            onClick={() => void sendFeedback("up")}
          >
            👍 팩트 일치
          </button>
          <button
            type="button"
            className="lr-studio-evidence-feedback-btn lr-studio-evidence-feedback-btn--warn"
            disabled={feedbackState === "sending"}
            onClick={() => void sendFeedback("down")}
          >
            👎 번역/맥락 이슈
          </button>
        </div>
        <div className="lr-studio-evidence-feedback-issue">
          <label htmlFor="lr-evidence-issue-type">이슈 분류</label>
          <select
            id="lr-evidence-issue-type"
            value={issueType}
            onChange={(e) =>
              setIssueType(
                (e.target.value as "translation" | "context" | "source" | "other") || "context",
              )
            }
          >
            <option value="translation">번역</option>
            <option value="context">문맥</option>
            <option value="source">출처</option>
            <option value="other">기타</option>
          </select>
        </div>
        {feedbackMsg ? (
          <p className="lr-studio-evidence-feedback-msg" role="status">
            {feedbackMsg}
          </p>
        ) : null}
        {feedbackSummary?.top_issue_types ? (
          <div className="lr-studio-evidence-issue-top">
            <p className="lr-studio-evidence-issue-top-title">최근 오류 유형 TOP</p>
            <ul>
              {[
                ["번역", feedbackSummary.top_issue_types.translation ?? 0],
                ["문맥", feedbackSummary.top_issue_types.context ?? 0],
                ["출처", feedbackSummary.top_issue_types.source ?? 0],
                ["기타", feedbackSummary.top_issue_types.other ?? 0],
              ]
                .filter(([, count]) => Number(count) > 0)
                .map(([label, count]) => (
                  <li key={String(label)}>
                    <span>{label}</span>
                    <strong>{count}</strong>
                  </li>
                ))}
            </ul>
          </div>
        ) : null}
        {feedbackSummary?.top_anchors?.length ? (
          <div className="lr-studio-evidence-anchor-top">
            <p className="lr-studio-evidence-issue-top-title">이슈 앵커 Drill-down</p>
            <ul>
              {feedbackSummary.top_anchors.slice(0, 5).map((item) => {
                const total = item.total ?? 0;
                const down = item.down ?? 0;
                const issueRate = total > 0 ? Math.round((down / total) * 100) : 0;
                return (
                  <li key={item.evidence_anchor || "unknown"}>
                    <span title={item.evidence_anchor || "unknown"}>
                      {(item.evidence_anchor || "unknown").slice(0, 32)}
                    </span>
                    <strong>{issueRate}%</strong>
                  </li>
                );
              })}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
