export type LogosTopologyHubV1 = {
  schema: "logos_corpus_4d_topology_hub_v1";
  generated_at_utc?: string;
  hypothesis_tier?: string;
  research_only?: boolean;
  n_verses?: number;
  global_centroid_4d?: { S: number; L: number; K: number; M: number };
  global_centrality_hubs?: Array<{
    verse_id: string;
    book_id?: string;
    hub_score_inverse_l2?: number;
    l2_to_global_centroid?: number;
    phase_angle_sl_rad?: number;
    vector_4d?: { S: number; L: number; K: number; M: number };
    interpretation_class?: string;
  }>;
  era_centroid_trajectories?: Array<{
    era_id: string;
    label_ko?: string;
    centroid_4d?: { S: number; L: number; K: number; M: number };
    phase_shift_l2_from_previous?: number;
    interpretation_class?: string;
  }>;
  book_centroid_top?: Array<{
    book_id: string;
    n_verses?: number;
    centroid_4d?: { S: number; L: number; K: number; M: number };
  }>;
  disclaimer_ko?: string;
  reproduce_command?: string;
};

export const UNIVERSE_HUB_LOGOS_TOPOLOGY_PATH = "/data/logos_corpus_4d_topology_hub_v1.json";

export function isLogosTopologyHubV1(data: unknown): data is LogosTopologyHubV1 {
  return (
    typeof data === "object" &&
    data !== null &&
    (data as LogosTopologyHubV1).schema === "logos_corpus_4d_topology_hub_v1"
  );
}
