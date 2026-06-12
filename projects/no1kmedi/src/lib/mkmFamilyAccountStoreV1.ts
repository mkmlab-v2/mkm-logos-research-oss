import { promises as fs } from "fs";
import path from "path";

import { newMkmAccountId } from "@/lib/mkmFamilySessionV1";
import type { MkmFamilyRpProduct } from "@/lib/mkmFamilyAuthConfigV1";

export type MkmFamilyAccountV1 = {
  schema: "mkm_family_account_v1";
  mkm_account_id: string;
  email: string;
  email_verified: boolean;
  display_name?: string;
  picture_url?: string;
  created_at_utc: string;
  updated_at_utc: string;
  auth_providers: Array<{ provider: "google"; provider_subject: string }>;
};

export type MkmFamilyProductLinkV1 = {
  schema: "mkm_family_product_link_v1";
  mkm_account_id: string;
  product: MkmFamilyRpProduct | "clinician" | "hub";
  product_profile_id: string;
  linked_at_utc: string;
};

const DATA_DIR = path.join(process.cwd(), "memory", "mkm_family");
const ACCOUNTS_FILE = path.join(DATA_DIR, "accounts_v1.json");
const LINKS_FILE = path.join(DATA_DIR, "product_links_v1.json");
const HANDOFF_FILE = path.join(DATA_DIR, "handoff_codes_v1.json");

export type HandoffCodeRow = {
  code: string;
  mkm_account_id: string;
  email: string;
  product: MkmFamilyRpProduct;
  product_profile_id: string;
  expires_at_utc: string;
  consumed: boolean;
};

async function ensureDir(): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
}

async function readJson<T>(filePath: string, fallback: T): Promise<T> {
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

async function writeJson<T>(filePath: string, data: T): Promise<void> {
  await ensureDir();
  await fs.writeFile(filePath, JSON.stringify(data, null, 2), "utf-8");
}

export async function listAccounts(): Promise<MkmFamilyAccountV1[]> {
  return readJson<MkmFamilyAccountV1[]>(ACCOUNTS_FILE, []);
}

export async function saveAccounts(rows: MkmFamilyAccountV1[]): Promise<void> {
  await writeJson(ACCOUNTS_FILE, rows);
}

export async function listProductLinks(): Promise<MkmFamilyProductLinkV1[]> {
  return readJson<MkmFamilyProductLinkV1[]>(LINKS_FILE, []);
}

export async function saveProductLinks(rows: MkmFamilyProductLinkV1[]): Promise<void> {
  await writeJson(LINKS_FILE, rows);
}

export async function listHandoffCodes(): Promise<HandoffCodeRow[]> {
  return readJson<HandoffCodeRow[]>(HANDOFF_FILE, []);
}

export async function saveHandoffCodes(rows: HandoffCodeRow[]): Promise<void> {
  const pruned = rows.filter((r) => new Date(r.expires_at_utc).getTime() > Date.now() - 60_000);
  await writeJson(HANDOFF_FILE, pruned);
}

function productProfileIdFor(product: MkmFamilyRpProduct, mkmAccountId: string): string {
  const suffix = mkmAccountId.replace(/^mkm_acc_/, "").slice(0, 24);
  if (product === "mkmlife") return `mkm_${suffix}`;
  return `pd_${suffix}`;
}

export async function upsertGoogleAccount(input: {
  email: string;
  email_verified: boolean;
  display_name?: string;
  picture_url?: string;
  google_sub: string;
}): Promise<MkmFamilyAccountV1> {
  const now = new Date().toISOString();
  const accounts = await listAccounts();
  const email = input.email.trim().toLowerCase();
  let account = accounts.find(
    (a) =>
      a.email === email ||
      a.auth_providers.some((p) => p.provider === "google" && p.provider_subject === input.google_sub),
  );

  if (account) {
    account.email = email;
    account.email_verified = input.email_verified;
    account.display_name = input.display_name || account.display_name;
    account.picture_url = input.picture_url || account.picture_url;
    account.updated_at_utc = now;
    const hasGoogle = account.auth_providers.some(
      (p) => p.provider === "google" && p.provider_subject === input.google_sub,
    );
    if (!hasGoogle) {
      account.auth_providers.push({ provider: "google", provider_subject: input.google_sub });
    }
  } else {
    account = {
      schema: "mkm_family_account_v1",
      mkm_account_id: newMkmAccountId(),
      email,
      email_verified: input.email_verified,
      display_name: input.display_name,
      picture_url: input.picture_url,
      created_at_utc: now,
      updated_at_utc: now,
      auth_providers: [{ provider: "google", provider_subject: input.google_sub }],
    };
    accounts.push(account);
  }

  await saveAccounts(accounts);
  return account;
}

export async function ensureProductLink(
  mkmAccountId: string,
  product: MkmFamilyRpProduct,
): Promise<MkmFamilyProductLinkV1> {
  const links = await listProductLinks();
  let link = links.find((l) => l.mkm_account_id === mkmAccountId && l.product === product);
  const now = new Date().toISOString();
  if (!link) {
    link = {
      schema: "mkm_family_product_link_v1",
      mkm_account_id: mkmAccountId,
      product,
      product_profile_id: productProfileIdFor(product, mkmAccountId),
      linked_at_utc: now,
    };
    links.push(link);
    await saveProductLinks(links);
  }
  return link;
}

export async function createHandoffCode(
  mkmAccountId: string,
  email: string,
  product: MkmFamilyRpProduct,
): Promise<{ code: string; product_profile_id: string; redirect_url: string }> {
  const link = await ensureProductLink(mkmAccountId, product);
  const code = `mkm_ho_${crypto.randomUUID().replace(/-/g, "")}`;
  const expires = new Date(Date.now() + 5 * 60 * 1000).toISOString();
  const rows = await listHandoffCodes();
  rows.push({
    code,
    mkm_account_id: mkmAccountId,
    email,
    product,
    product_profile_id: link.product_profile_id,
    expires_at_utc: expires,
    consumed: false,
  });
  await saveHandoffCodes(rows);
  return { code, product_profile_id: link.product_profile_id, redirect_url: "" };
}

export async function consumeHandoffCode(code: string): Promise<HandoffCodeRow | null> {
  const rows = await listHandoffCodes();
  const row = rows.find((r) => r.code === code && !r.consumed);
  if (!row) return null;
  if (new Date(row.expires_at_utc).getTime() < Date.now()) return null;
  row.consumed = true;
  await saveHandoffCodes(rows);
  return row;
}

export async function findAccountById(mkmAccountId: string): Promise<MkmFamilyAccountV1 | null> {
  const accounts = await listAccounts();
  return accounts.find((a) => a.mkm_account_id === mkmAccountId) ?? null;
}
