export type GraphNodeKind =
  | "symptom"
  | "pattern_hypothesis"
  | "sasang_hint"
  | "plan_candidate"
  | "red_flag"
  | "anchor"
  | "bundle_slot";

export type GraphNode = {
  id: string;
  label: string;
  kind: GraphNodeKind;
  confidence_band?: "low" | "mid" | "high";
  non_gating?: boolean;
  evidence_count?: number;
};

export type GraphEdge = {
  id: string;
  from: string;
  to: string;
  relation: "supports" | "conflicts" | "caution" | "derived_from";
};

export type ConflictInterpretation = {
  id: string;
  label: string;
  source: string;
  non_gating?: boolean;
};

export type ConflictGroup = {
  id: string;
  label: string;
  interpretations: ConflictInterpretation[];
  status: "open";
};

export type RationaleStep = {
  step: number;
  from_label: string;
  to_label: string;
  relation: GraphEdge["relation"];
};

export type GraphBundleV1 = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  safety_flags: string[];
  non_gating_labels: string[];
  conflict_groups?: ConflictGroup[];
  rationale_steps?: RationaleStep[];
};

export type GraphBuildResponse = {
  success: boolean;
  error?: string;
  request_id?: string;
  graph_bundle_v1?: GraphBundleV1;
};

export type GraphReviewFeedback = "up" | "down" | "hold";
