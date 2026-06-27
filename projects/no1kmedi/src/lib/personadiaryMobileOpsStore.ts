"use client";

import {
  hydrateOpsFromCachedConsumerProfile,
  syncConsumerProfileFromOps,
} from "./personadiaryConsumerProfileV1";
import {
  createDefaultPersonadiaryMobileOps,
  normalizePersonadiaryMobileOps,
  PERSONADIARY_MOBILE_OPS_IDB_KEY,
  type PersonadiaryMobileOpsV1,
} from "./personadiaryMobileOpsV1";

const DB_NAME = "personadiary_mobile_ops_v1";
const DB_VERSION = 2;
const STORE = "ops";
const QUEUE_STORE = "ingest_queue";
/** Capacitor WebView IDB can hang — fail open to in-memory default (preview_only). */
export const PERSONADIARY_IDB_OPEN_TIMEOUT_MS = 6000;
export const PERSONADIARY_IDB_READ_TIMEOUT_MS = 6000;

function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error(`${label}_timeout`)), ms);
    promise.then(
      (value) => {
        window.clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        window.clearTimeout(timer);
        reject(error);
      }
    );
  });
}

function openDb(): Promise<IDBDatabase> {
  return withTimeout(
    new Promise((resolve, reject) => {
      if (typeof indexedDB === "undefined") {
        reject(new Error("indexeddb_unavailable"));
        return;
      }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onerror = () => reject(req.error ?? new Error("idb_open_failed"));
      req.onblocked = () => reject(new Error("idb_open_blocked"));
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE);
        }
        if (!db.objectStoreNames.contains(QUEUE_STORE)) {
          db.createObjectStore(QUEUE_STORE);
        }
      };
      req.onsuccess = () => resolve(req.result);
    }),
    PERSONADIARY_IDB_OPEN_TIMEOUT_MS,
    "idb_open"
  );
}

export type PersonadiaryMobileOpsLoadSource = "indexeddb" | "default_fallback";

export async function loadPersonadiaryMobileOps(): Promise<{
  doc: PersonadiaryMobileOpsV1;
  source: PersonadiaryMobileOpsLoadSource;
}> {
  try {
    const db = await openDb();
    try {
      const doc = await withTimeout(
        new Promise<PersonadiaryMobileOpsV1>((resolve, reject) => {
          const tx = db.transaction(STORE, "readonly");
          tx.onerror = () => reject(tx.error ?? new Error("idb_tx_failed"));
          const getReq = tx.objectStore(STORE).get(PERSONADIARY_MOBILE_OPS_IDB_KEY);
          getReq.onerror = () => reject(getReq.error ?? new Error("idb_get_failed"));
          getReq.onsuccess = () => {
            try {
              const raw = getReq.result as PersonadiaryMobileOpsV1 | undefined;
              if (!raw || raw.schema !== "personadiary_mobile_ops_v1") {
                resolve(
                  normalizePersonadiaryMobileOps(
                    hydrateOpsFromCachedConsumerProfile(createDefaultPersonadiaryMobileOps())
                  )
                );
                return;
              }
              resolve(normalizePersonadiaryMobileOps(hydrateOpsFromCachedConsumerProfile(raw)));
            } catch {
              resolve(createDefaultPersonadiaryMobileOps());
            }
          };
        }),
        PERSONADIARY_IDB_READ_TIMEOUT_MS,
        "idb_read"
      );
      return { doc, source: "indexeddb" };
    } finally {
      db.close();
    }
  } catch {
    return {
      doc: normalizePersonadiaryMobileOps(
        hydrateOpsFromCachedConsumerProfile(createDefaultPersonadiaryMobileOps())
      ),
      source: "default_fallback",
    };
  }
}

export async function savePersonadiaryMobileOps(
  doc: PersonadiaryMobileOpsV1
): Promise<PersonadiaryMobileOpsV1> {
  const normalized = normalizePersonadiaryMobileOps(doc);
  syncConsumerProfileFromOps(normalized);
  const db = await openDb();
  try {
    await withTimeout(
      new Promise<void>((resolve, reject) => {
        const tx = db.transaction(STORE, "readwrite");
        tx.onerror = () => reject(tx.error ?? new Error("idb_tx_failed"));
        const putReq = tx.objectStore(STORE).put(normalized, PERSONADIARY_MOBILE_OPS_IDB_KEY);
        putReq.onerror = () => reject(putReq.error ?? new Error("idb_put_failed"));
        putReq.onsuccess = () => resolve();
      }),
      PERSONADIARY_IDB_READ_TIMEOUT_MS,
      "idb_write"
    );
  } finally {
    db.close();
  }
  return normalized;
}

export function exportPersonadiaryMobileOpsJson(doc: PersonadiaryMobileOpsV1): string {
  return JSON.stringify(normalizePersonadiaryMobileOps(doc), null, 2);
}

export function downloadPersonadiaryMobileOpsExport(doc: PersonadiaryMobileOpsV1): void {
  const blob = new Blob([exportPersonadiaryMobileOpsJson(doc)], {
    type: "application/json;charset=utf-8",
  });
  triggerJsonDownload(blob, `personadiary_mobile_ops_${doc.week_label || "export"}.json`);
}

export function parsePersonadiaryMobileOpsImport(raw: string): PersonadiaryMobileOpsV1 {
  const parsed = JSON.parse(raw) as PersonadiaryMobileOpsV1;
  if (parsed?.schema !== "personadiary_mobile_ops_v1") {
    throw new Error("invalid_schema");
  }
  return normalizePersonadiaryMobileOps(parsed);
}

export async function importPersonadiaryMobileOpsFromJson(
  raw: string
): Promise<PersonadiaryMobileOpsV1> {
  const doc = parsePersonadiaryMobileOpsImport(raw);
  return savePersonadiaryMobileOps(doc);
}

export function triggerJsonDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
