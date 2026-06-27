import { NextRequest, NextResponse } from "next/server";

import type { ConflictGroup, GraphBundleV1, GraphEdge, GraphNode, RationaleStep } from "@/lib/clinicianGraphTypesV1";

type BuildRequest = {
  schema: "clinician_graph_build_from_cds_request_v1";
  request_id: string;
  cds_envelope: Record<string, unknown>;
  reasoning?: {
    syndrome_hypothesis?: string;
    care_direction?: string;
    caution?: string;
  };
  patient_care_bundle?: Record<string, unknown>;
  options?: {
    include_sasang_hint?: boolean;
    include_conflict_paths?: boolean;
    include_bundle_slots?: boolean;
  };
};

function asText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function confidenceFromScore(score: number | undefined): GraphNode["confidence_band"] {
  if (score == null || Number.isNaN(score)) return "mid";
  if (score >= 0.65) return "high";
  if (score >= 0.35) return "mid";
  return "low";
}

function attachEvidenceCounts(nodes: GraphNode[], edges: GraphEdge[]): GraphNode[] {
  const counts = new Map<string, number>();
  for (const edge of edges) {
    counts.set(edge.to, (counts.get(edge.to) || 0) + 1);
  }
  return nodes.map((node) => ({
    ...node,
    evidence_count: counts.get(node.id) || 0,
  }));
}

function buildRationaleSteps(nodes: GraphNode[], edges: GraphEdge[]): RationaleStep[] {
  const labelById = new Map(nodes.map((n) => [n.id, n.label]));
  return edges.slice(0, 12).map((edge, idx) => ({
    step: idx + 1,
    from_label: labelById.get(edge.from) || edge.from,
    to_label: labelById.get(edge.to) || edge.to,
    relation: edge.relation,
  }));
}

function buildConflictGroups(
  patternNodes: GraphNode[],
  westernNodes: GraphNode[],
  sasangNode: GraphNode | null,
): ConflictGroup[] {
  const groups: ConflictGroup[] = [];

  if (patternNodes.length >= 2) {
    groups.push({
      id: "conflict:pattern_candidates",
      label: "변증 후보 간 상충 가능",
      status: "open",
      interpretations: patternNodes.map((n) => ({
        id: n.id,
        label: n.label,
        source: "tri_layer_or_reasoning",
        non_gating: false,
      })),
    });
  }

  if (patternNodes.length && westernNodes.length) {
    groups.push({
      id: "conflict:km_vs_western",
      label: "한의 변증 vs 서양 감별 (참고)",
      status: "open",
      interpretations: [
        ...patternNodes.slice(0, 2).map((n) => ({
          id: n.id,
          label: n.label,
          source: "km_pattern",
          non_gating: false,
        })),
        ...westernNodes.slice(0, 2).map((n) => ({
          id: n.id,
          label: n.label,
          source: "western_differential",
          non_gating: true,
        })),
      ],
    });
  }

  if (sasangNode && patternNodes.length) {
    groups.push({
      id: "conflict:sasang_vs_pattern",
      label: "사상 힌트 vs 변증 후보 (NON_GATING)",
      status: "open",
      interpretations: [
        {
          id: patternNodes[0].id,
          label: patternNodes[0].label,
          source: "pattern_hypothesis",
          non_gating: false,
        },
        {
          id: sasangNode.id,
          label: sasangNode.label,
          source: "sasang_hint",
          non_gating: true,
        },
      ],
    });
  }

  return groups.slice(0, 3);
}

export async function POST(request: NextRequest) {
  let body: BuildRequest;
  try {
    body = (await request.json()) as BuildRequest;
  } catch {
    return NextResponse.json({ success: false, error: "invalid_json" }, { status: 400 });
  }

  if (body.schema !== "clinician_graph_build_from_cds_request_v1") {
    return NextResponse.json({ success: false, error: "invalid_schema" }, { status: 400 });
  }
  if (!asText(body.request_id)) {
    return NextResponse.json({ success: false, error: "missing_request_id" }, { status: 400 });
  }
  if (body.cds_envelope?.schema !== "km_physician_cds_assist_envelope_v1") {
    return NextResponse.json({ success: false, error: "invalid_cds_envelope_schema" }, { status: 400 });
  }

  const envelope = body.cds_envelope;
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const safetyFlags: string[] = [];
  const nonGatingLabels = ["sasang_hint", "myeongni_season_hint", "western_differential"];
  const patternNodes: GraphNode[] = [];
  const westernNodes: GraphNode[] = [];
  let sasangNode: GraphNode | null = null;

  const reqNodeId = `req:${body.request_id}`;
  nodes.push({ id: reqNodeId, label: body.request_id, kind: "anchor", confidence_band: "high" });

  const syndrome = asText(body.reasoning?.syndrome_hypothesis);
  if (syndrome) {
    const id = "pattern:syndrome_hypothesis";
    const node: GraphNode = { id, label: syndrome.slice(0, 120), kind: "pattern_hypothesis", confidence_band: "mid" };
    nodes.push(node);
    patternNodes.push(node);
    edges.push({ id: `e:${reqNodeId}:${id}`, from: reqNodeId, to: id, relation: "derived_from" });
  }

  const triLayer = asRecord(envelope.mkm_bianzheng_tri_layer);
  const layerA = triLayer ? asRecord(triLayer.layer_a_engine) : null;
  for (const raw of asArray(layerA?.candidate_list)) {
    const cand = asRecord(raw);
    const label = asText(cand?.label);
    const candId = asText(cand?.candidate_id) || `cand:${nodes.length}`;
    if (!label) continue;
    const id = `pattern:${candId}`;
    if (nodes.some((n) => n.id === id)) continue;
    const score = typeof cand?.score_0_1 === "number" ? cand.score_0_1 : undefined;
    const node: GraphNode = {
      id,
      label: label.slice(0, 120),
      kind: "pattern_hypothesis",
      confidence_band: confidenceFromScore(score),
    };
    nodes.push(node);
    patternNodes.push(node);
    edges.push({ id: `e:${reqNodeId}:${id}`, from: reqNodeId, to: id, relation: "derived_from" });
  }

  for (const raw of asArray(envelope.differential_framework)) {
    const diff = asRecord(raw);
    const label = asText(diff?.label);
    if (!label) continue;
    const id = `pattern:diff:${nodes.length}`;
    const node: GraphNode = {
      id,
      label: label.slice(0, 120),
      kind: "pattern_hypothesis",
      confidence_band: "low",
    };
    nodes.push(node);
    patternNodes.push(node);
    edges.push({ id: `e:${reqNodeId}:${id}`, from: reqNodeId, to: id, relation: "derived_from" });
  }

  const layerB = triLayer ? asRecord(triLayer.layer_b_augmentation) : null;
  const western = layerB ? asRecord(layerB.western_med_fallback) : null;
  for (const raw of asArray(western?.differential_hypotheses)) {
    const hyp = asRecord(raw);
    const label = asText(hyp?.label);
    const hypId = asText(hyp?.hypothesis_id) || `wm:${nodes.length}`;
    if (!label) continue;
    const id = `western:${hypId}`;
    const node: GraphNode = {
      id,
      label: label.slice(0, 120),
      kind: "pattern_hypothesis",
      confidence_band: "low",
      non_gating: true,
    };
    nodes.push(node);
    westernNodes.push(node);
    edges.push({ id: `e:${reqNodeId}:${id}`, from: reqNodeId, to: id, relation: "derived_from" });
  }

  const care = asText(body.reasoning?.care_direction);
  if (care) {
    const id = "plan:care_direction";
    nodes.push({ id, label: care.slice(0, 120), kind: "plan_candidate", confidence_band: "mid" });
    edges.push({ id: `e:${reqNodeId}:${id}`, from: reqNodeId, to: id, relation: "supports" });
  }

  for (const step of asArray(envelope.suggested_next_steps_for_physician)) {
    const text = asText(step);
    if (!text) continue;
    const id = `plan:step:${nodes.length}`;
    nodes.push({ id, label: text.slice(0, 120), kind: "plan_candidate", confidence_band: "mid" });
    edges.push({ id: `e:${reqNodeId}:${id}`, from: reqNodeId, to: id, relation: "supports" });
  }

  const caution = asText(body.reasoning?.caution);
  if (caution) {
    const id = "flag:caution";
    nodes.push({ id, label: caution.slice(0, 120), kind: "red_flag", confidence_band: "high" });
    edges.push({ id: `e:${reqNodeId}:${id}`, from: reqNodeId, to: id, relation: "caution" });
    safetyFlags.push(caution.slice(0, 200));
  }

  for (const raw of asArray(envelope.red_flags_and_escalation)) {
    const text = asText(raw);
    if (!text) continue;
    const id = `flag:red:${nodes.length}`;
    nodes.push({ id, label: text.slice(0, 120), kind: "red_flag", confidence_band: "high" });
    edges.push({ id: `e:${reqNodeId}:${id}`, from: reqNodeId, to: id, relation: "caution" });
    if (!safetyFlags.includes(text.slice(0, 200))) {
      safetyFlags.push(text.slice(0, 200));
    }
  }

  if (body.options?.include_sasang_hint) {
    const sasangText = asText(triLayer?.sasang) || asText(envelope.sasang_hint);
    if (sasangText) {
      const id = "hint:sasang";
      sasangNode = {
        id,
        label: sasangText.slice(0, 120),
        kind: "sasang_hint",
        confidence_band: "low",
        non_gating: true,
      };
      nodes.push(sasangNode);
      edges.push({ id: `e:${reqNodeId}:${id}`, from: reqNodeId, to: id, relation: "derived_from" });
    }
  }

  if (body.options?.include_bundle_slots && body.patient_care_bundle?.schema === "patient_care_bundle_v1") {
    const bundleId = asText(body.patient_care_bundle.bundle_id) || "bundle";
    const bundleAnchorId = `bundle:${bundleId}`;
    nodes.push({
      id: bundleAnchorId,
      label: `bundle:${bundleId.slice(0, 8)}`,
      kind: "anchor",
      confidence_band: "high",
    });
    edges.push({
      id: `e:${reqNodeId}:${bundleAnchorId}`,
      from: reqNodeId,
      to: bundleAnchorId,
      relation: "derived_from",
    });

    for (const raw of asArray(body.patient_care_bundle.patient_slots)) {
      const slot = asRecord(raw);
      if (!slot || slot.included === false) continue;
      const slotId = asText(slot.slot_id);
      const title = asText(slot.title) || slotId;
      if (!slotId) continue;
      const trustTier = asText(slot.trust_tier);
      const nonGating =
        trustTier === "hypo_reference" ||
        trustTier === "non_gating_symbolic" ||
        slotId === "sasang" ||
        slotId === "myeongni_ref" ||
        slotId === "logos_opt";
      const kind: GraphNode["kind"] =
        slotId === "sasang" ? "sasang_hint" : slotId === "core" ? "plan_candidate" : "bundle_slot";
      const id = `slot:${slotId}`;
      const node: GraphNode = {
        id,
        label: title.slice(0, 120),
        kind,
        confidence_band: nonGating ? "low" : "mid",
        non_gating: nonGating,
      };
      nodes.push(node);
      edges.push({
        id: `e:${bundleAnchorId}:${id}`,
        from: bundleAnchorId,
        to: id,
        relation: slotId === "core" ? "supports" : "derived_from",
      });
      if (slotId === "sasang" && !sasangNode) {
        sasangNode = node;
      }
    }
  }

  const nodesWithCounts = attachEvidenceCounts(nodes, edges);
  const conflictGroups = body.options?.include_conflict_paths
    ? buildConflictGroups(patternNodes, westernNodes, sasangNode)
    : [];
  const rationaleSteps = buildRationaleSteps(nodesWithCounts, edges);

  const graphBundle: GraphBundleV1 = {
    nodes: nodesWithCounts,
    edges,
    safety_flags: safetyFlags,
    non_gating_labels: nonGatingLabels,
    conflict_groups: conflictGroups,
    rationale_steps: rationaleSteps,
  };

  return NextResponse.json(
    {
      success: true,
      request_id: body.request_id,
      graph_bundle_v1: graphBundle,
      boundary: {
        physician_confirmation_required: true,
        non_gating_graph_hints: true,
        not_standalone_diagnosis: true,
      },
    },
    { status: 200, headers: { "Cache-Control": "no-store" } },
  );
}
