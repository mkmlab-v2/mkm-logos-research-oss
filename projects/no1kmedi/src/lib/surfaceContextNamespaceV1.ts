/** JEMA OS namespace v1 — read domain_surface_hint from handoff JSON (UI wire). */
export type JemaOsNamespaceV1 = {
  domain_surface_hint: string
  match_rule_id: string
  resolved_by: string
  source?: Record<string, string>
  research_only?: boolean
  pointer_bag_only?: boolean
}

/** domain_surface_hint → API domain_lane (SSOT: domain_namespace_surface_map_v1 surfaces.*.domain_tag) */
const HINT_TO_DOMAIN_LANE: Record<string, string> = {
  logos: 'logos',
  finance: 'finance',
  health: 'health',
  cs: 'cs_ticket_triage',
  hub: 'hub',
  enterprise: 'enterprise_herbs_formulas',
  coding: 'code',
  ide: 'code',
}

export type AskSurfaceContext = {
  domain_surface_hint: string
  domain_lane: string
  match_rule_id: string
  resolved_by: string
}

export function domainLaneFromSurfaceHint(hint: string | null | undefined): string {
  const key = (hint || '').trim().toLowerCase()
  if (!key) return 'logos'
  return HINT_TO_DOMAIN_LANE[key] || key
}

export function readDomainSurfaceHint(
  handoff: { namespace_v1?: JemaOsNamespaceV1 | null } | null | undefined,
): string | null {
  const hint = handoff?.namespace_v1?.domain_surface_hint
  return typeof hint === 'string' && hint.trim() ? hint.trim().toLowerCase() : null
}

/** Attach to intake / compress API payloads from hub or mkmlife handoff. */
export function namespaceIntakeHeaders(
  handoff: { namespace_v1?: JemaOsNamespaceV1 | null } | null | undefined,
): Record<string, string> {
  const hint = readDomainSurfaceHint(handoff)
  if (!hint) return {}
  return { 'X-JEMA-Domain-Surface-Hint': hint }
}

function _hintFromLocation(hostname: string, pathname: string): { hint: string; rule: string } {
  const host = hostname.toLowerCase()
  const path = pathname.toLowerCase()
  if (host.includes('logos.jema-ai.com') || path.startsWith('/logos-research')) {
    return { hint: 'logos', rule: 'logos_subdomain_or_path' }
  }
  if (path.startsWith('/enterprise')) return { hint: 'enterprise', rule: 'jema_enterprise_path' }
  if (path.startsWith('/hub')) return { hint: 'hub', rule: 'jema_hub_path' }
  if (path.startsWith('/cs')) return { hint: 'cs', rule: 'jema_cs_path' }
  if (path.startsWith('/ide') || path.startsWith('/developer-support')) {
    return { hint: 'coding', rule: 'jema_developer_path' }
  }
  return { hint: 'logos', rule: 'default_logos_ask' }
}

/** Client-side resolver for Logos Ask — no model download; KB wire only. */
export function resolveAskSurfaceContext(options?: {
  handoff?: { namespace_v1?: JemaOsNamespaceV1 | null } | null
  searchParams?: URLSearchParams | null
}): AskSurfaceContext {
  const fromHandoff = readDomainSurfaceHint(options?.handoff)
  const fromQuery = options?.searchParams?.get('surface_hint')?.trim().toLowerCase() || null

  let hint = fromQuery || fromHandoff
  let rule = fromHandoff ? 'handoff_namespace_v1' : 'pending'

  if (!hint && typeof window !== 'undefined') {
    const loc = _hintFromLocation(window.location.hostname, window.location.pathname)
    hint = loc.hint
    rule = loc.rule
  }

  if (!hint) {
    hint = 'logos'
    rule = 'default_logos_ask'
  }

  return {
    domain_surface_hint: hint,
    domain_lane: domainLaneFromSurfaceHint(hint),
    match_rule_id: rule,
    resolved_by: 'surfaceContextNamespaceV1.resolveAskSurfaceContext',
  }
}
