export type UniverseHubRq025OracleCardV1 = {
  schema: string;
  version: string;
  research_only: boolean;
  hypothesis_tag: string;
  gating: string;
  rq_id: string;
  title_ko: string;
  last_updated_utc: string;
  summary_ko: string;
  arms_label_ko: string;
  verdict: {
    any_beats_majority: boolean;
    track_a_promotion: boolean;
    oracle_promotion: boolean;
  };
  discovery_note_ko: string;
  data_ssot: string;
  forbidden_on_surface: string[];
};

export const UNIVERSE_HUB_RQ025_CARD_PATH = "/data/universe_hub_rq025_oracle_card_v1.json";

export async function loadUniverseHubRq025OracleCardV1(): Promise<UniverseHubRq025OracleCardV1 | null> {
  try {
    const res = await fetch(UNIVERSE_HUB_RQ025_CARD_PATH, { cache: "no-store" });
    if (!res.ok) return null;
    const data = (await res.json()) as UniverseHubRq025OracleCardV1;
    if (data.schema !== "universe_hub_rq025_oracle_card_v1") return null;
    return data;
  } catch {
    return null;
  }
}
