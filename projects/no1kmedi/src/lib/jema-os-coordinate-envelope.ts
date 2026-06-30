export type JemaOsReadDepth = 'skim' | 'deep' | 'hold'

export type JemaOsCoordinateEnvelope = {
  schema: string
  version: string
  generated_at_utc: string
  send_gate: string
  research_only: boolean
  read_depth: JemaOsReadDepth
  umr_binding: {
    resolution_tier: string
    required_ltm_depth: number
    domain_tag: string
    epistemic_grade: string
    resume_mode_hint: string
  }
  ltm_pin: {
    concept_id: string
    software_layer: string
    lane: string
  }
  a2a_peer?: {
    optional?: boolean
    peer_handoff_pointer?: string | null
    bounded_lane_loop_ref?: string | null
    bounded_lane_pin_ref?: string | null
  }
  fail_comp_004_guard: {
    compression_kpi_weight_in_inference: number
    lens_score_headline_merge: boolean
  }
}

export const COORDINATE_ENVELOPE_API = '/api/v1/hub/coordinate-envelope'

export async function fetchCoordinateEnvelope(
  readDepth: JemaOsReadDepth = 'skim',
): Promise<JemaOsCoordinateEnvelope | null> {
  try {
    const res = await fetch(`${COORDINATE_ENVELOPE_API}?read_depth=${readDepth}`, {
      cache: 'no-store',
    })
    if (!res.ok) return null
    return (await res.json()) as JemaOsCoordinateEnvelope
  } catch {
    return null
  }
}
