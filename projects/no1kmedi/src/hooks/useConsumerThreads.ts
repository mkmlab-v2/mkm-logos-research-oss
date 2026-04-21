"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ConsumerChatThread } from "@/lib/consumer-chat-types";
import {
  createEmptyThread,
  loadConsumerThreads,
  saveConsumerThreads,
  titleFromTurns,
} from "@/lib/consumer-chat-storage";

export function useConsumerThreads() {
  const [ready, setReady] = useState(false);
  const [threads, setThreads] = useState<ConsumerChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  useEffect(() => {
    let list = loadConsumerThreads();
    if (!list.length) {
      const first = createEmptyThread();
      list = [first];
      saveConsumerThreads(list);
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
    const t = createEmptyThread();
    setThreads((prev) => {
      const merged = [t, ...prev];
      saveConsumerThreads(merged);
      return merged;
    });
    setActiveThreadId(t.id);
    return t.id;
  }, []);

  const deleteThread = useCallback((id: string) => {
    setThreads((prev) => {
      const next = prev.filter((t) => t.id !== id);
      if (!next.length) {
        const t = createEmptyThread();
        saveConsumerThreads([t]);
        setActiveThreadId(t.id);
        return [t];
      }
      saveConsumerThreads(next);
      setActiveThreadId((cur) => (cur === id ? next[0].id : cur));
      return next;
    });
  }, []);

  const commitThread = useCallback((patch: Partial<ConsumerChatThread> & { id: string }) => {
    setThreads((prev) => {
      const cur = prev.find((t) => t.id === patch.id);
      if (!cur) return prev;
      const turns = patch.turns ?? cur.turns;
      const health = patch.health ?? cur.health;
      const next: ConsumerChatThread = {
        ...cur,
        ...patch,
        turns,
        health,
        title: patch.title ?? titleFromTurns(turns),
        updatedAt: Date.now(),
      };
      const others = prev.filter((t) => t.id !== next.id);
      const merged = [next, ...others];
      saveConsumerThreads(merged);
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
