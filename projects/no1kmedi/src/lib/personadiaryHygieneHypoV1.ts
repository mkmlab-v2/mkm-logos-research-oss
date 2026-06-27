export const HYGIENE_BOUNDARY_ACK =
  "research_only · local IndexedDB tidy · no push · no OS app block · no server upload";

export type PersonadiaryHygienePrefsHypoV1 = {
  hypothesis_tier: "B";
  boundary_ack: string;
  pull_window_local?: string;
  last_hygiene_run_utc?: string;
  last_guide_prefetch_utc?: string;
  native_shell_target?: "web_pwa" | "capacitor_hypo_v1";
};

export type HygieneRunStats = {
  checkpoints_before: number;
  checkpoints_after: number;
  diary_before: number;
  diary_after: number;
  duplicates_removed: number;
};

export function createDefaultHygienePrefs(): PersonadiaryHygienePrefsHypoV1 {
  return {
    hypothesis_tier: "B",
    boundary_ack: HYGIENE_BOUNDARY_ACK,
    pull_window_local: "21:00",
    native_shell_target: "web_pwa",
  };
}

export function normalizeHygienePrefs(
  raw: PersonadiaryHygienePrefsHypoV1 | undefined
): PersonadiaryHygienePrefsHypoV1 | undefined {
  if (!raw || raw.hypothesis_tier !== "B") return undefined;
  const pull = raw.pull_window_local?.trim();
  const pullOk = pull && /^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(pull) ? pull : "21:00";
  return {
    hypothesis_tier: "B",
    boundary_ack: String(raw.boundary_ack || HYGIENE_BOUNDARY_ACK).slice(0, 512),
    pull_window_local: pullOk,
    last_hygiene_run_utc: raw.last_hygiene_run_utc,
    last_guide_prefetch_utc: raw.last_guide_prefetch_utc,
    native_shell_target:
      raw.native_shell_target === "capacitor_hypo_v1" ? "capacitor_hypo_v1" : "web_pwa",
  };
}

/** True when local clock is within ±15 minutes of pull_window_local (HH:MM). */
export function isPullWindowNow(pullWindowLocal: string, now = new Date()): boolean {
  const m = /^([01][0-9]|2[0-3]):([0-5][0-9])$/.exec(pullWindowLocal.trim());
  if (!m) return false;
  const targetMin = Number(m[1]) * 60 + Number(m[2]);
  const nowMin = now.getHours() * 60 + now.getMinutes();
  const diff = Math.abs(targetMin - nowMin);
  return diff <= 15 || diff >= 24 * 60 - 15;
}

export function runLocalHygiene<T extends {
  checkpoints: { ts_utc: string; one_line: string }[];
  diary_entries_local: { date_local: string; body: string; lane: string; synced?: boolean }[];
}>(ops: T): { ops: T; stats: HygieneRunStats } {
  const checkpointsBefore = ops.checkpoints.length;
  const diaryBefore = ops.diary_entries_local.length;

  const seenCp = new Set<string>();
  const checkpoints = ops.checkpoints.filter((cp) => {
    const key = `${cp.ts_utc}::${cp.one_line}`;
    if (seenCp.has(key)) return false;
    seenCp.add(key);
    return true;
  });

  const byDate = new Map<string, (typeof ops.diary_entries_local)[0]>();
  for (const entry of ops.diary_entries_local) {
    byDate.set(entry.date_local, entry);
  }
  const diary_entries_local = Array.from(byDate.values())
    .sort((a, b) => a.date_local.localeCompare(b.date_local))
    .slice(-366)
    .map((e) => ({ ...e, synced: false }));

  return {
    ops: { ...ops, checkpoints, diary_entries_local },
    stats: {
      checkpoints_before: checkpointsBefore,
      checkpoints_after: checkpoints.length,
      diary_before: diaryBefore,
      diary_after: diary_entries_local.length,
      duplicates_removed:
        checkpointsBefore - checkpoints.length + (diaryBefore - diary_entries_local.length),
    },
  };
}
