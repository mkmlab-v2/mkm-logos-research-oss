/** logos.jema-ai.com JEMA OS research handoff — public JSON loader */
import type { LogosTextMvpHandoffSummary } from "./logosResearchTextMvpV1";
import { DEFAULT_TEXT_MVP_HANDOFF } from "./logosResearchTextMvpV1";

export type LogosJemaAiResearchHandoffV1 = {
  schema: "logos_jema_ai_research_handoff_v1";
  surface?: {
    domain?: string;
    path?: string;
    mode?: string;
    metering_enabled?: boolean;
    live_llm_on_surface?: boolean;
    graphics_studio_excluded?: boolean;
  };
  brand?: { public_name?: string; product_line_ko?: string };
  governance?: {
    send_gate?: string;
    research_only?: boolean;
    disclaimer_ko?: string;
    disclaimer_en?: string;
  };
  consumer_handoff?: {
    mkmlife_oracle_sphere_url?: string;
    mkmlife_send_gate?: string;
    mkmlife_inference_runtime_active?: boolean;
    consumer_sku_note_ko?: string;
  };
  api_contract?: {
    page_path?: string;
    post_path?: string;
    output_format?: string;
  };
  namespace_v1?: {
    domain_surface_hint: string;
    match_rule_id: string;
    resolved_by: string;
    source?: Record<string, string>;
    research_only?: boolean;
    pointer_bag_only?: boolean;
  };
};

const HANDOFF_PATH = "/data/logos_jema_ai_research_handoff_v1.json";

export async function fetchLogosJemaAiResearchHandoff(): Promise<LogosJemaAiResearchHandoffV1 | null> {
  try {
    const res = await fetch(HANDOFF_PATH, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as LogosJemaAiResearchHandoffV1;
  } catch {
    return null;
  }
}

export function handoffToTextMvpSummary(doc: LogosJemaAiResearchHandoffV1 | null): LogosTextMvpHandoffSummary {
  if (!doc) return DEFAULT_TEXT_MVP_HANDOFF;
  const surface = doc.surface ?? {};
  const consumer = doc.consumer_handoff ?? {};
  const domain = String(surface.domain ?? "logos.jema-ai.com").replace(/^https?:\/\//, "");
  const pagePath = String(surface.path ?? "/logos-research/ask");
  return {
    logos_surface: `${domain}${pagePath}`,
    mkmlife_oracle_sphere_url:
      consumer.mkmlife_oracle_sphere_url ?? DEFAULT_TEXT_MVP_HANDOFF.mkmlife_oracle_sphere_url,
    consumer_sku_note_ko: consumer.consumer_sku_note_ko ?? DEFAULT_TEXT_MVP_HANDOFF.consumer_sku_note_ko,
    inference_queue_armed: consumer.mkmlife_inference_runtime_active === true,
  };
}
