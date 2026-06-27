/** Layer B embed SSOT — logos_graph_studio_layer_b_ux_contract_v1.json */
export const LOGOS_GRAPH_STUDIO_QA_BASE =
  "https://logos.jema-ai.com/logos-research/studio";

export const LOGOS_GRAPH_STUDIO_DEFAULT_PRESET = "job_job_suffering_reason";

/** Layer B contract query fragment (smoke marker). */
export const LOGOS_LAYER_B_EMBED_QUERY = "embed=hero";

export function buildLogosGraphStudioEmbedUrl(opts?: {
  preset?: string;
  embed?: boolean;
  autoplay?: boolean;
  loop?: boolean;
}): string {
  const preset = opts?.preset ?? LOGOS_GRAPH_STUDIO_DEFAULT_PRESET;
  const params = new URLSearchParams();
  params.set("preset", preset);
  params.set("autorun", opts?.autoplay !== false ? "1" : "0");
  if (opts?.embed !== false) {
    params.set("embed", "hero");
    params.set("demo", "1");
  }
  return `${LOGOS_GRAPH_STUDIO_QA_BASE}?${params.toString()}`;
}
