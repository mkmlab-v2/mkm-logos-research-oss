"use client";

import {
  createEmptyIngestQueue,
  normalizeIngestQueue,
  PERSONADIARY_OFFLINE_INGEST_QUEUE_IDB_KEY,
  type PersonadiaryOfflineIngestQueueV1,
} from "./personadiaryOfflineIngestQueueV1";

const DB_NAME = "personadiary_mobile_ops_v1";
const DB_VERSION = 2;
const OPS_STORE = "ops";
const QUEUE_STORE = "ingest_queue";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("indexeddb_unavailable"));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error ?? new Error("idb_open_failed"));
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(OPS_STORE)) {
        db.createObjectStore(OPS_STORE);
      }
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        db.createObjectStore(QUEUE_STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
  });
}

export async function loadPersonadiaryIngestQueue(): Promise<PersonadiaryOfflineIngestQueueV1> {
  try {
    const db = await openDb();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(QUEUE_STORE, "readonly");
      const getReq = tx.objectStore(QUEUE_STORE).get(PERSONADIARY_OFFLINE_INGEST_QUEUE_IDB_KEY);
      getReq.onerror = () => reject(getReq.error ?? new Error("idb_get_failed"));
      getReq.onsuccess = () => {
        const doc = getReq.result as PersonadiaryOfflineIngestQueueV1 | undefined;
        if (!doc || doc.schema !== "personadiary_offline_ingest_queue_v1") {
          resolve(createEmptyIngestQueue());
          return;
        }
        resolve(normalizeIngestQueue(doc));
      };
    });
  } catch {
    return createEmptyIngestQueue();
  }
}

export async function savePersonadiaryIngestQueue(
  doc: PersonadiaryOfflineIngestQueueV1
): Promise<PersonadiaryOfflineIngestQueueV1> {
  const normalized = normalizeIngestQueue(doc);
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, "readwrite");
    const putReq = tx.objectStore(QUEUE_STORE).put(normalized, PERSONADIARY_OFFLINE_INGEST_QUEUE_IDB_KEY);
    putReq.onerror = () => reject(putReq.error ?? new Error("idb_put_failed"));
    putReq.onsuccess = () => resolve();
  });
  return normalized;
}
