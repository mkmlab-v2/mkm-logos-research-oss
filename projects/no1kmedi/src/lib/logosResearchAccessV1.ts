import type { NextRequest } from "next/server";

import { isJtiRevoked } from "@/lib/logosAgentAuthStoreV1";
import { verifyLogosAgentAccessToken } from "@/lib/logosAgentAuthJwtV1";
import type { LogosAgentScope } from "@/lib/logosAgentAuthTypesV1";
import { isProApiKey } from "@/lib/logosResearchQuotaV1";

export type LogosAccessContext = {
  pro: boolean;
  via: "api_key" | "agent_token" | "none";
  email?: string;
  registration_id?: string;
  scopes: LogosAgentScope[];
};

function parseBearer(request: NextRequest): string | null {
  const header = request.headers.get("authorization")?.trim();
  if (!header?.toLowerCase().startsWith("bearer ")) return null;
  const token = header.slice(7).trim();
  return token || null;
}

export async function resolveLogosAccess(
  request: NextRequest,
  requiredScope?: LogosAgentScope,
): Promise<LogosAccessContext> {
  if (isProApiKey(request)) {
    return { pro: true, via: "api_key", scopes: [] };
  }

  const bearer = parseBearer(request);
  if (bearer) {
    const claims = verifyLogosAgentAccessToken(bearer);
    if (claims && !(await isJtiRevoked(claims.jti))) {
      if (!requiredScope || claims.scopes.includes(requiredScope)) {
        return {
          pro: true,
          via: "agent_token",
          email: claims.email,
          registration_id: claims.sub,
          scopes: claims.scopes,
        };
      }
    }
  }

  return { pro: false, via: "none", scopes: [] };
}

export function hasLogosProAccess(access: LogosAccessContext): boolean {
  return access.pro;
}
