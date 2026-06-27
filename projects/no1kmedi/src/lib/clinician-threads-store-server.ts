import { promises as fs } from "fs";
import path from "path";
import type { ClinicianChatThread } from "@/lib/clinician-chat-types";
import { normalizeClinicianThreads } from "@/lib/clinician-chat-storage";

const DATA_DIR = path.join(process.cwd(), "memory", "commercialization");
const STORE_FILE = path.join(DATA_DIR, "clinician_threads_store.json");
const STORE_VERSION = 1;

type AccountRecord = {
  updatedAt: number;
  threads: ClinicianChatThread[];
};

type StoreShape = {
  v: number;
  accounts: Record<string, AccountRecord>;
};

function emptyStore(): StoreShape {
  return { v: STORE_VERSION, accounts: {} };
}

async function ensureDir(): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
}

async function readStore(): Promise<StoreShape> {
  try {
    const raw = await fs.readFile(STORE_FILE, "utf-8");
    const parsed = JSON.parse(raw) as StoreShape;
    if (!parsed || typeof parsed !== "object" || parsed.v !== STORE_VERSION || !parsed.accounts) {
      return emptyStore();
    }
    return parsed;
  } catch {
    return emptyStore();
  }
}

async function writeStore(store: StoreShape): Promise<void> {
  await ensureDir();
  await fs.writeFile(STORE_FILE, JSON.stringify(store, null, 2), "utf-8");
}

export function normalizeClinicianEmailKey(email: string): string {
  return email.trim().toLowerCase();
}

export async function getClinicianThreadsForEmail(email: string): Promise<ClinicianChatThread[]> {
  const key = normalizeClinicianEmailKey(email);
  if (!key) return [];
  const store = await readStore();
  const rec = store.accounts[key];
  if (!rec) return [];
  return normalizeClinicianThreads({ v: 1, threads: rec.threads });
}

export async function saveClinicianThreadsForEmail(
  email: string,
  threads: ClinicianChatThread[],
): Promise<{ savedAt: number; count: number }> {
  const key = normalizeClinicianEmailKey(email);
  if (!key) throw new Error("email_required");
  const normalized = normalizeClinicianThreads({ v: 1, threads });
  const now = Date.now();
  const store = await readStore();
  store.accounts[key] = { updatedAt: now, threads: normalized };
  await writeStore(store);
  return { savedAt: now, count: normalized.length };
}
