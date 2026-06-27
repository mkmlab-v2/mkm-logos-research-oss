export const LOGOS_AGENT_AUTH_GRANT_CLAIM =
  "urn:workos:agent-auth:grant-type:claim" as const;

export const LOGOS_AGENT_SCOPES = [
  "logos.presets.read",
  "logos.query.read",
  "logos.evidence.write",
  "logos.lead.write",
] as const;

export type LogosAgentScope = (typeof LOGOS_AGENT_SCOPES)[number];

export type LogosAgentRegistrationType = "service_auth";

export type LogosAgentRegistrationRecord = {
  registration_id: string;
  registration_type: LogosAgentRegistrationType;
  login_hint: string;
  claim_token: string;
  claim_token_expires: string;
  user_code: string;
  user_code_expires: string;
  claim_attempt_token: string;
  post_claim_scopes: LogosAgentScope[];
  claimed: boolean;
  claimed_at?: string;
  created_at: string;
};

export type LogosAgentAccessClaims = {
  sub: string;
  email: string;
  scope: LogosAgentScope[];
  jti: string;
};
