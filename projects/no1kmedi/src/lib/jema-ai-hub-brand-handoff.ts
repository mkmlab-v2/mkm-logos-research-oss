export type JemaAiHubBrandHandoff = {
  schema: string
  generated_at_utc: string
  surface: {
    domain: string
    path: string
    mode: string
    hub_llm_enabled: boolean
    metering_enabled: boolean
    track_a_promotion_allowed: boolean
  }
  brand: {
    hub_display: string
    public_os_display: string
    public_os_name: string
    internal_kernel: string
    rename_policy: string
  }
  governance: {
    send_gate: string
    research_only: boolean
    disclaimer_ko: string
    disclaimer_en: string
  }
  cta_links: { key: string; href: string; label: string; sublabel: string }[]
  pipeline_snapshot: {
    hybrid_chain_ok: boolean
    freeze_manifest_ok: boolean
    sidecar_verse_count: number | null
    lemma_edge_line_count: number | null
    cloud_llm_called: boolean
  }
}

export const JEMA_AI_HUB_HANDOFF_DATA_URL = '/data/jema_ai_hub_brand_handoff_v1.json'

export async function fetchJemaAiHubBrandHandoff(): Promise<JemaAiHubBrandHandoff | null> {
  try {
    const res = await fetch(JEMA_AI_HUB_HANDOFF_DATA_URL, { cache: 'no-store' })
    if (!res.ok) return null
    return (await res.json()) as JemaAiHubBrandHandoff
  } catch {
    return null
  }
}
