/** Logos agent-auth discovery constants (auth.md Tier A + well-known stubs). */

export const LOGOS_CANONICAL_ORIGIN = "https://logos.jema-ai.com";

export const LOGOS_AGENT_AUTH_V1 = {
  schema: "logos_agent_auth_discovery_v1",
  implementation_status: "tier_c_service_auth",
  research_only: true,
  send_gate: "HOLD",
  non_gating: true,
  resource: `${LOGOS_CANONICAL_ORIGIN}/`,
  resource_name: "Logos Scripture Research Workspace",
  resource_logo_uri: `${LOGOS_CANONICAL_ORIGIN}/logos-research/opengraph-image`,
  authorization_server: LOGOS_CANONICAL_ORIGIN,
  skill: `${LOGOS_CANONICAL_ORIGIN}/auth.md`,
  scopes_supported: [
    "logos.presets.read",
    "logos.query.read",
    "logos.evidence.write",
    "logos.lead.write",
  ],
  identity_types_supported: ["service_auth"],
  assertion_types_supported: [] as string[],
  legacy_pro_api_key_header: "x-logos-api-key",
  pilot_lead_url: `${LOGOS_CANONICAL_ORIGIN}/logos-research#pilot-lead`,
  docs_url: `${LOGOS_CANONICAL_ORIGIN}/logos-research/docs/pilot-scope`,
  protocol_reference: "https://github.com/workos/auth.md",
} as const;

export function logosProtectedResourceMetadata() {
  const a = LOGOS_AGENT_AUTH_V1;
  return {
    resource: a.resource,
    resource_name: a.resource_name,
    resource_logo_uri: a.resource_logo_uri,
    authorization_servers: [a.authorization_server],
    scopes_supported: [...a.scopes_supported],
    bearer_methods_supported: ["header"],
    logos_agent_auth: {
      implementation_status: a.implementation_status,
      skill: a.skill,
      research_only: a.research_only,
      send_gate: a.send_gate,
      legacy_pro_api_key_header: a.legacy_pro_api_key_header,
      pilot_lead_url: a.pilot_lead_url,
    },
  };
}

export function logosAuthorizationServerMetadata() {
  const a = LOGOS_AGENT_AUTH_V1;
  const base = a.authorization_server;
  return {
    resource: a.resource,
    authorization_servers: [a.authorization_server],
    scopes_supported: [...a.scopes_supported],
    bearer_methods_supported: ["header"],
    issuer: base,
    token_endpoint: `${base}/api/agent/oauth2/token`,
    revocation_endpoint: `${base}/api/agent/oauth2/revoke`,
    grant_types_supported: [
      "urn:ietf:params:oauth:grant-type:jwt-bearer",
      "urn:workos:agent-auth:grant-type:claim",
    ],
    implementation_status: a.implementation_status,
    agent_auth: {
      skill: a.skill,
      identity_endpoint: `${base}/api/agent/identity`,
      claim_endpoint: `${base}/api/agent/identity/claim`,
      events_endpoint: `${base}/api/agent/event/notify`,
      identity_types_supported: [...a.identity_types_supported],
      identity_assertion: {
        assertion_types_supported: [...a.assertion_types_supported],
      },
      events_supported: [
        "https://schemas.workos.com/events/agent/auth/identity/assertion/revoked",
      ],
      endpoints_status: "live_service_auth",
      fallback: {
        pilot_lead_url: a.pilot_lead_url,
        legacy_pro_api_key_header: a.legacy_pro_api_key_header,
      },
    },
  };
}
