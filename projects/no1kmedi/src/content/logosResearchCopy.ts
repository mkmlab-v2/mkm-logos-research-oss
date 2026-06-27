import data from "../../marketing-site/logos-research-copy.json";

export type LogosResearchMetrics = {
  schema?: string;
  generated_at_utc?: string;
  metrics?: {
    graphrag_seed_organic?: string;
    llm_citation_valid_themes?: string;
    shared_hubs?: number;
    insight_total_units?: number;
    ledger_records?: number;
    path_verification_pass_rate?: number;
    path_verification_gate_pass?: boolean;
    b2b_structure_map_verdict?: string;
    phase_o_ok?: boolean;
    integration_closure_ok?: boolean;
  };
};

export const logosResearchCopy = data;
