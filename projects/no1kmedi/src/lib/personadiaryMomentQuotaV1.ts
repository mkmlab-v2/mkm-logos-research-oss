/**
 * Free-tier moment ask quota — client-only (preview · no server billing).
 */
const STORAGE_KEY = "pd_moment_quota_v1";
export const MOMENT_FREE_DAILY_LIMIT = 3;

type QuotaRecord = {
  date_kst: string;
  used: number;
};

export function kstDateKey(d = new Date()): string {
  return d.toLocaleDateString("en-CA", { timeZone: "Asia/Seoul" });
}

function readRecord(): QuotaRecord {
  if (typeof localStorage === "undefined") {
    return { date_kst: kstDateKey(), used: 0 };
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { date_kst: kstDateKey(), used: 0 };
    const doc = JSON.parse(raw) as QuotaRecord;
    const today = kstDateKey();
    if (doc.date_kst !== today) return { date_kst: today, used: 0 };
    return { date_kst: today, used: Math.max(0, Number(doc.used) || 0) };
  } catch {
    return { date_kst: kstDateKey(), used: 0 };
  }
}

function writeRecord(rec: QuotaRecord): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(rec));
}

export type MomentQuotaState = {
  date_kst: string;
  used: number;
  limit: number;
  remaining: number;
  at_limit: boolean;
};

export function getMomentQuotaState(): MomentQuotaState {
  const rec = readRecord();
  const remaining = Math.max(0, MOMENT_FREE_DAILY_LIMIT - rec.used);
  return {
    date_kst: rec.date_kst,
    used: rec.used,
    limit: MOMENT_FREE_DAILY_LIMIT,
    remaining,
    at_limit: remaining <= 0,
  };
}

export function canAskMoment(): boolean {
  return getMomentQuotaState().remaining > 0;
}

export function consumeMomentQuota(): MomentQuotaState {
  const rec = readRecord();
  const next = { date_kst: rec.date_kst, used: Math.min(MOMENT_FREE_DAILY_LIMIT, rec.used + 1) };
  writeRecord(next);
  return getMomentQuotaState();
}
