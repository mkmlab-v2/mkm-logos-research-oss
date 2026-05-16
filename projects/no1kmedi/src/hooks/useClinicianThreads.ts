"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ClinicianChatThread } from "@/lib/clinician-chat-types";
import {
  createEmptyClinicianThread,
  loadClinicianThreads,
  saveClinicianThreads,
  titleFromClinicianTurns,
} from "@/lib/clinician-chat-storage";

export function useClinicianThreads() {
  const [ready, setReady] = useState(false);
  const [threads, setThreads] = useState<ClinicianChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  useEffect(() => {
    let list = loadClinicianThreads();
    if (!list.length) {
      const first = createEmptyClinicianThread();
      list = [first];
      saveClinicianThreads(list);
      setActiveThreadId(first.id);
    } else {
      list = [...list].sort((a, b) => b.updatedAt - a.updatedAt);
      setActiveThreadId(list[0].id);
    }
    setThreads(list);
    setReady(true);
  }, []);

  const activeThread = useMemo(() => {
    if (!activeThreadId) return threads[0] ?? null;
    return threads.find((t) => t.id === activeThreadId) ?? threads[0] ?? null;
  }, [threads, activeThreadId]);

  const createThread = useCallback(() => {
    const t = createEmptyClinicianThread();
    setThreads((prev) => {
      const merged = [t, ...prev];
      saveClinicianThreads(merged);
      return merged;
    });
    setActiveThreadId(t.id);
    return t.id;
  }, []);

  const deleteThread = useCallback((id: string) => {
    setThreads((prev) => {
      const next = prev.filter((t) => t.id !== id);
      if (!next.length) {
        const t = createEmptyClinicianThread();
        saveClinicianThreads([t]);
        setActiveThreadId(t.id);
        return [t];
      }
      saveClinicianThreads(next);
      setActiveThreadId((cur) => (cur === id ? next[0].id : cur));
      return next;
    });
  }, []);

  const commitThread = useCallback((patch: Partial<ClinicianChatThread> & { id: string }) => {
    setThreads((prev) => {
      const cur = prev.find((t) => t.id === patch.id);
      if (!cur) return prev;
      const turns = patch.turns ?? cur.turns;
      const context = patch.context ?? cur.context;
      const next: ClinicianChatThread = {
        ...cur,
        ...patch,
        turns,
        context,
        title: patch.title ?? titleFromClinicianTurns(turns),
        updatedAt: Date.now(),
      };
      const others = prev.filter((t) => t.id !== next.id);
      const merged = [next, ...others];
      saveClinicianThreads(merged);
      return merged;
    });
  }, []);

  return {
    ready,
    threads,
    activeThreadId,
    setActiveThreadId,
    activeThread,
    createThread,
    deleteThread,
    commitThread,
  };
}
