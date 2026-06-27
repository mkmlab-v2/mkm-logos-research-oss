import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import type { LogosAgentRegistrationRecord } from "@/lib/logosAgentAuthTypesV1";

type StoreDoc = {
  schema: "logos_agent_auth_store_v1";
  registrations: Record<string, LogosAgentRegistrationRecord>;
  revoked_jti: string[];
};

function dataDir(): string {
  return (
    process.env.LOGOS_AGENT_AUTH_DATA_DIR?.trim() || path.join(process.cwd(), ".data")
  );
}

function storePath(): string {
  return path.join(dataDir(), "logos_agent_auth_store_v1.json");
}

async function loadStore(): Promise<StoreDoc> {
  const file = storePath();
  try {
    const raw = await readFile(file, "utf8");
    const parsed = JSON.parse(raw) as StoreDoc;
    if (parsed?.schema === "logos_agent_auth_store_v1" && parsed.registrations) {
      return {
        schema: "logos_agent_auth_store_v1",
        registrations: parsed.registrations,
        revoked_jti: Array.isArray(parsed.revoked_jti) ? parsed.revoked_jti : [],
      };
    }
  } catch {
    // fresh store
  }
  return { schema: "logos_agent_auth_store_v1", registrations: {}, revoked_jti: [] };
}

async function saveStore(doc: StoreDoc): Promise<void> {
  await mkdir(dataDir(), { recursive: true });
  await writeFile(storePath(), `${JSON.stringify(doc, null, 2)}\n`, "utf8");
}

export async function getRegistration(
  registrationId: string,
): Promise<LogosAgentRegistrationRecord | null> {
  const doc = await loadStore();
  return doc.registrations[registrationId] ?? null;
}

export async function getRegistrationByClaimToken(
  claimToken: string,
): Promise<LogosAgentRegistrationRecord | null> {
  const doc = await loadStore();
  for (const row of Object.values(doc.registrations)) {
    if (row.claim_token === claimToken) return row;
  }
  return null;
}

export async function getRegistrationByClaimAttemptToken(
  claimAttemptToken: string,
): Promise<LogosAgentRegistrationRecord | null> {
  const doc = await loadStore();
  for (const row of Object.values(doc.registrations)) {
    if (row.claim_attempt_token === claimAttemptToken) return row;
  }
  return null;
}

export async function putRegistration(row: LogosAgentRegistrationRecord): Promise<void> {
  const doc = await loadStore();
  doc.registrations[row.registration_id] = row;
  await saveStore(doc);
}

export async function isJtiRevoked(jti: string): Promise<boolean> {
  const doc = await loadStore();
  return doc.revoked_jti.includes(jti);
}

export async function revokeJti(jti: string): Promise<void> {
  const doc = await loadStore();
  if (!doc.revoked_jti.includes(jti)) doc.revoked_jti.push(jti);
  if (doc.revoked_jti.length > 5000) {
    doc.revoked_jti = doc.revoked_jti.slice(-2500);
  }
  await saveStore(doc);
}

export async function countRecentRegistrationsForEmail(
  email: string,
  windowMs: number,
): Promise<number> {
  const doc = await loadStore();
  const since = Date.now() - windowMs;
  const norm = email.trim().toLowerCase();
  let n = 0;
  for (const row of Object.values(doc.registrations)) {
    if (row.login_hint.toLowerCase() !== norm) continue;
    if (Date.parse(row.created_at) >= since) n += 1;
  }
  return n;
}
