"use client";

import dynamic from "next/dynamic";
import { useCallback, useMemo, useState } from "react";

import { fetchClinicianGraphFromCds } from "@/lib/clinicianGraphBuildClientV1";
import { trackClinicianGraphBuild, trackClinicianGraphViewMode } from "@/lib/clinicianGraphPilotKpiV1";
import type { GraphBundleV1, GraphNode, GraphReviewFeedback, RationaleStep } from "@/lib/clinicianGraphTypesV1";
import { submitGraphReviewFeedback } from "@/lib/clinicianGraphReviewFeedbackV1";

const ClinicianConsultGraphViz = dynamic(
  () => import("@/components/ClinicianConsultGraphViz").then((m) => ({ default: m.ClinicianConsultGraphViz })),
  {
    loading: () => <p className="workspace-muted">그래프 시각화 로딩…</p>,
    ssr: false,
  },
);

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

export function ClinicianConsultGraphPanel({ requestId, envelope, reasoning, patientCareBundle }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [graphBundle, setGraphBundle] = useState<GraphBundleV1 | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "graph">("list");
  const [feedbackBusy, setFeedbackBusy] = useState<string | null>(null);
  const [feedbackState, setFeedbackState] = useState<Record<string, GraphReviewFeedback>>({});

  const canBuild = useMemo(() => Boolean(requestId && envelope?.schema), [envelope, requestId]);
  const nodes = graphBundle?.nodes || [];
  const edges = graphBundle?.edges || [];
  const safetyFlags = graphBundle?.safety_flags || [];
  const rationaleSteps = graphBundle?.rationale_steps || [];

  const buildGraph = useCallback(async () => {
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
      setGraphBundle(bundle);
      trackClinicianGraphBuild(requestId, {
        node_count: bundle.nodes.length,
        edge_count: bundle.edges.length,
        conflict_group_count: bundle.conflict_groups?.length || 0,
        has_bundle_slots: Boolean(patientCareBundle),
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "graph_build_failed");
    } finally {
      setLoading(false);
    }
  }, [canBuild, envelope, patientCareBundle, reasoning, requestId]);

  const onNodeFeedback = useCallback(
    async (nodeId: string, feedback: GraphReviewFeedback) => {
      setFeedbackBusy(nodeId);
      setError(null);
      const result = await submitGraphReviewFeedback({
        encounterRef: requestId,
        targetId: nodeId,
        targetKind: "node",
        feedback,
        reasonCode: feedback === "down" ? "graph_node_disagree" : undefined,
      });
      setFeedbackBusy(null);
      if (!result.success) {
        setError(result.error || "review_feedback_failed");
        return;
      }
      setFeedbackState((prev) => ({ ...prev, [nodeId]: feedback }));
    },
    [requestId],
  );

  const renderNodeRow = (n: GraphNode) => (
    <li key={n.id} className="consult-graph-node-item">
      <span>
        [{n.kind}] {n.label}
        {n.non_gating ? " · NON_GATING" : ""}
        {typeof n.evidence_count === "number" ? ` · 근거 ${n.evidence_count}` : ""}
        {n.confidence_band ? ` · ${n.confidence_band}` : ""}
      </span>
      <span className="consult-graph-feedback-row">
        {(["up", "hold", "down"] as const).map((fb) => (
          <button
            key={fb}
            type="button"
            className={`btn btn-ghost consult-graph-fb-btn${feedbackState[n.id] === fb ? " is-active" : ""}`}
            disabled={feedbackBusy === n.id}
            onClick={() => void onNodeFeedback(n.id, fb)}
            title={fb === "up" ? "동의" : fb === "hold" ? "보류" : "반대"}
          >
            {fb === "up" ? "👍" : fb === "hold" ? "⏸" : "👎"}
          </button>
        ))}
      </span>
    </li>
  );

  return (
    <div className="workspace-panel workspace-panel--prose clinician-canvas-graph-panel">
      <h3 className="workspace-panel-title">근거 그래프 (검토 보조)</h3>
      <p className="workspace-muted">
        자동 진단/처방이 아닌 검토 보조 패널입니다. 사상·명리·서양 감별·번들 슬롯은 <code>NON_GATING</code>으로 표시됩니다.
      </p>
      {patientCareBundle ? (
        <p className="consult-source-chip">patient_care_bundle 연동됨 · 슬롯 노드 포함</p>
      ) : null}
      <div className="workspace-actions-row">
        <button type="button" className="workspace-secondary-btn" onClick={() => void buildGraph()} disabled={loading || !canBuild}>
          {loading ? "그래프 생성 중…" : "그래프 생성"}
        </button>
        {nodes.length ? (
          <>
            <button
              type="button"
              className={`workspace-secondary-btn${viewMode === "list" ? " is-active" : ""}`}
              onClick={() => {
                setViewMode("list");
                trackClinicianGraphViewMode(requestId, "list");
              }}
            >
              목록
            </button>
            <button
              type="button"
              className={`workspace-secondary-btn${viewMode === "graph" ? " is-active" : ""}`}
              onClick={() => {
                setViewMode("graph");
                trackClinicianGraphViewMode(requestId, "graph");
              }}
            >
              시각화
            </button>
          </>
        ) : null}
      </div>
      {error ? <p className="workspace-error-text">{error}</p> : null}
      {nodes.length ? (
        <div className="notice-box">
          <p>
            노드 {nodes.length} · 엣지 {edges.length}
          </p>
          {viewMode === "graph" && graphBundle ? <ClinicianConsultGraphViz graphBundle={graphBundle} /> : null}
          {viewMode === "list" ? <ul className="consult-graph-node-list">{nodes.slice(0, 12).map(renderNodeRow)}</ul> : null}
          {rationaleSteps.length ? (
            <>
              <p>근거 경로 (요약):</p>
              <ol>
                {rationaleSteps.slice(0, 6).map((step: RationaleStep) => (
                  <li key={`${step.step}:${step.to_label}`}>
                    {step.from_label} → {step.to_label} ({step.relation})
                  </li>
                ))}
              </ol>
            </>
          ) : null}
          {safetyFlags.length ? (
            <>
              <p>Safety flags:</p>
              <ul>
                {safetyFlags.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      ) : (
        <p className="workspace-muted">CDS 봉투 기준 그래프를 생성해 원장 검토용 근거를 표시합니다.</p>
      )}
    </div>
  );
}
