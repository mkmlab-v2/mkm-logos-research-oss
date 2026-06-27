"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchClinicianGraphFromCds } from "@/lib/clinicianGraphBuildClientV1";
import { trackClinicianGraphSignoff } from "@/lib/clinicianGraphPilotKpiV1";
import type { ConflictGroup, GraphReviewFeedback, RationaleStep } from "@/lib/clinicianGraphTypesV1";
import { submitGraphReviewFeedback } from "@/lib/clinicianGraphReviewFeedbackV1";

type Props = {
  requestId: string;
  envelope: Record<string, unknown>;
  reasoning?: {
    syndrome_hypothesis?: string;
    care_direction?: string;
    caution?: string;
  };
  patientCareBundle?: Record<string, unknown> | null;
};

export function ClinicianGraphConflictSheet({ requestId, envelope, reasoning, patientCareBundle }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<ConflictGroup[]>([]);
  const [rationaleSteps, setRationaleSteps] = useState<RationaleStep[]>([]);
  const [slotCount, setSlotCount] = useState(0);
  const [clinicianNote, setClinicianNote] = useState("");
  const [signOffChecks, setSignOffChecks] = useState({
    reviewedCds: false,
    resolvedConflicts: false,
    noAutoSend: false,
  });
  const [feedbackState, setFeedbackState] = useState<Record<string, GraphReviewFeedback>>({});
  const [feedbackBusy, setFeedbackBusy] = useState<string | null>(null);
  const [signOffSaved, setSignOffSaved] = useState(false);

  const canBuild = useMemo(() => Boolean(requestId && envelope?.schema), [envelope, requestId]);
  const signOffReady = signOffChecks.reviewedCds && signOffChecks.resolvedConflicts && signOffChecks.noAutoSend;

  const buildSheet = useCallback(async () => {
    if (!canBuild) return;
    setLoading(true);
    setError(null);
    try {
      const bundle = await fetchClinicianGraphFromCds({
        requestId,
        envelope,
        reasoning,
        patientCareBundle,
      });
      setConflicts(bundle.conflict_groups || []);
      setRationaleSteps(bundle.rationale_steps || []);
      setSlotCount(bundle.nodes.filter((n) => n.kind === "bundle_slot" || n.id.startsWith("slot:")).length);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "graph_build_failed");
    } finally {
      setLoading(false);
    }
  }, [canBuild, envelope, patientCareBundle, reasoning, requestId]);

  useEffect(() => {
    if (canBuild) void buildSheet();
  }, [buildSheet, canBuild]);

  const onConflictFeedback = useCallback(
    async (groupId: string, feedback: GraphReviewFeedback) => {
      setFeedbackBusy(groupId);
      setError(null);
      const result = await submitGraphReviewFeedback({
        encounterRef: requestId,
        targetId: groupId,
        targetKind: "node",
        feedback,
        reasonCode: "conflict_group_review",
        clinicianNote: clinicianNote || undefined,
      });
      setFeedbackBusy(null);
      if (!result.success) {
        setError(result.error || "review_feedback_failed");
        return;
      }
      setFeedbackState((prev) => ({ ...prev, [groupId]: feedback }));
    },
    [clinicianNote, requestId],
  );

  const saveSignOff = useCallback(async () => {
    if (!signOffReady) return;
    setFeedbackBusy("signoff");
    setError(null);
    const result = await submitGraphReviewFeedback({
      encounterRef: requestId,
      targetId: `signoff:${requestId}`,
      targetKind: "node",
      feedback: "up",
      reasonCode: "physician_signoff_checklist",
      clinicianNote: clinicianNote || "checklist_complete",
    });
    setFeedbackBusy(null);
    if (!result.success) {
      setError(result.error || "signoff_failed");
      return;
    }
    setSignOffSaved(true);
    trackClinicianGraphSignoff(requestId);
  }, [clinicianNote, requestId, signOffReady]);

  return (
    <div className="workspace-panel workspace-panel--prose consult-conflict-sheet clinician-canvas-conflict-sheet">
      <h3 className="workspace-panel-title">상충 해석 · 근거 경로</h3>
      <p className="workspace-muted">
        병렬 해석과 근거 단계를 검토합니다. 최종 확정은 한의사 판단이며, 사상·명리·서양 감별은 NON_GATING 참고입니다.
      </p>
      {patientCareBundle ? (
        <p className="consult-source-chip">
          번들 슬롯 연동 · slot 노드 {slotCount}개
        </p>
      ) : null}
      <div className="workspace-actions-row">
        <button type="button" className="workspace-secondary-btn" onClick={() => void buildSheet()} disabled={loading || !canBuild}>
          {loading ? "갱신 중…" : "상충 시트 갱신"}
        </button>
      </div>
      {error ? <p className="workspace-error-text">{error}</p> : null}

      {conflicts.length ? (
        <div className="consult-conflict-groups">
          {conflicts.map((group) => (
            <div key={group.id} className="notice-box consult-conflict-card">
              <strong>{group.label}</strong>
              <ul>
                {group.interpretations.map((item) => (
                  <li key={item.id}>
                    {item.label}
                    {item.non_gating ? " · NON_GATING" : ""}
                    <span className="workspace-muted"> ({item.source})</span>
                  </li>
                ))}
              </ul>
              <div className="consult-graph-feedback-row">
                {(["up", "hold", "down"] as const).map((fb) => (
                  <button
                    key={fb}
                    type="button"
                    className={`btn btn-ghost consult-graph-fb-btn${feedbackState[group.id] === fb ? " is-active" : ""}`}
                    disabled={feedbackBusy === group.id}
                    onClick={() => void onConflictFeedback(group.id, fb)}
                  >
                    {fb === "up" ? "확정 방향" : fb === "hold" ? "보류" : "기각"}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="workspace-muted">현재 봉투에서 자동 추출된 상충 그룹이 없습니다. 번들 생성 후 갱신하면 슬롯 기반 경로가 추가될 수 있습니다.</p>
      )}

      {rationaleSteps.length ? (
        <div className="notice-box">
          <strong>근거 경로 (step chain)</strong>
          <ol>
            {rationaleSteps.map((step) => (
              <li key={`${step.step}:${step.to_label}`}>
                {step.step}. {step.from_label} → {step.to_label} ({step.relation})
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      <div className="consult-signoff-block">
        <strong>원장 메모 · 확정 체크</strong>
        <textarea
          className="consult-signoff-note"
          rows={3}
          placeholder="상충 해석 메모 (내부 기록)"
          value={clinicianNote}
          onChange={(e) => setClinicianNote(e.target.value)}
        />
        <div className="consult-bundle-options">
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={signOffChecks.reviewedCds}
              onChange={(e) => setSignOffChecks((s) => ({ ...s, reviewedCds: e.target.checked }))}
            />
            CDS 보조 초안을 검토했습니다
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={signOffChecks.resolvedConflicts}
              onChange={(e) => setSignOffChecks((s) => ({ ...s, resolvedConflicts: e.target.checked }))}
            />
            상충 해석을 확정 또는 보류 처리했습니다
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={signOffChecks.noAutoSend}
              onChange={(e) => setSignOffChecks((s) => ({ ...s, noAutoSend: e.target.checked }))}
            />
            환자 대외 발송 전 추가 검토가 필요함을 확인했습니다
          </label>
        </div>
        <button type="button" className="btn btn-primary" disabled={!signOffReady || feedbackBusy === "signoff"} onClick={() => void saveSignOff()}>
          {signOffSaved ? "확정 기록됨" : "검토 확정 기록"}
        </button>
      </div>
    </div>
  );
}
