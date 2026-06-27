import type { ClinicianChatThread } from "@/lib/clinician-chat-types";
import { normalizeClinicianThreads } from "@/lib/clinician-chat-storage";

export type ClinicianThreadsApiResponse = {
  success: boolean;
  error?: string;
  threads?: ClinicianChatThread[];
  savedAt?: number;
  count?: number;
  sync_source?: string;
};

export function mergeClinicianThreadLists(
  local: ClinicianChatThread[],
  remote: ClinicianChatThread[],
): ClinicianChatThread[] {
  const byId = new Map<string, ClinicianChatThread>();
  for (const t of remote) byId.set(t.id, t);
  for (const t of local) {
    const existing = byId.get(t.id);
    if (!existing || (t.updatedAt || 0) >= (existing.updatedAt || 0)) {
      byId.set(t.id, t);
    }
  }
  return [...byId.values()].sort((a, b) => b.updatedAt - a.updatedAt);
}

export async function fetchClinicianThreadsRemote(email: string): Promise<ClinicianChatThread[]> {
  const res = await fetch(`/api/clinician/threads?email=${encodeURIComponent(email)}`, {
    method: "GET",
    cache: "no-store",
  });
  const json = (await res.json()) as ClinicianThreadsApiResponse;
  if (!res.ok || !json.success) return [];
  return normalizeClinicianThreads({ v: 1, threads: json.threads ?? [] });
}

export async function pushClinicianThreadsRemote(
  email: string,
  threads: ClinicianChatThread[],
): Promise<boolean> {
  const res = await fetch(`/api/clinician/threads?email=${encodeURIComponent(email)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ threads }),
  });
  const json = (await res.json()) as ClinicianThreadsApiResponse;
  return res.ok && json.success === true;
}

export function threadMatchesSearch(t: ClinicianChatThread, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const hay = [
    t.patientLabel,
    t.title,
    t.sessionDate,
    ...t.turns.map((x) => x.message),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(q);
}
