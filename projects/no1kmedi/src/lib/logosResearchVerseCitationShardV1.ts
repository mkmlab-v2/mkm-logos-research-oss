"use client";

import { useEffect, useState } from "react";

export const LOGOS_VERSE_CITATION_SHARD_URL =
  "/data/logos_studio/verse_citation_shard_v1.json";

export type VerseCitationShardEntry = {
  ref: string;
  text_ko: string;
  translation_id: string;
  stage_id?: string | null;
  stage_label_ko?: string | null;
  bottleneck_ko?: string | null;
  verse_note_ko?: string | null;
  governance?: string;
};

export type VerseCitationShardDoc = {
  schema_version: string;
  verses: Record<string, VerseCitationShardEntry>;
};

export function lookupVerseCitationShard(
  ref: string,
  doc: VerseCitationShardDoc | null,
): VerseCitationShardEntry | null {
  if (!doc?.verses) return null;
  return doc.verses[ref] || null;
}

export function isVersificationProxyEntry(entry: VerseCitationShardEntry | null): boolean {
  return Boolean(entry?.governance?.includes("versification_proxy"));
}

export function useLogosVerseCitationShard(enabled = true) {
  const [shardDoc, setShardDoc] = useState<VerseCitationShardDoc | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(LOGOS_VERSE_CITATION_SHARD_URL, { cache: "force-cache" });
        if (!res.ok) throw new Error(`verse_shard_http_${res.status}`);
        const data = (await res.json()) as VerseCitationShardDoc;
        if (!cancelled) {
          setShardDoc(data);
          setLoadError(null);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : "verse_shard_failed");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return { shardDoc, loadError };
}
