"use client";

const BLOOM_INDEX_URL = "/data/logos_studio/bloom_31k_index_v1.json";
const BLOOM_SHARD_BASE = "/data/logos_studio/bloom_shards_v1";

export type BloomChapterShard = {
  schema: string;
  shard_id: string;
  book: string;
  chapter: number;
  verse_count: number;
  verse_refs: string[];
  research_only?: boolean;
};

export type Bloom31kIndex = {
  schema: string;
  chapter_shard_count: number;
  public_shard_dir: string;
  chapter_shards: Array<{
    shard_id: string;
    book: string;
    chapter: number;
    verse_count: number;
    public_url: string;
  }>;
};

let indexCache: Bloom31kIndex | null = null;
const shardCache = new Map<string, BloomChapterShard>();

function parseRef(ref: string): { book: string; chapter: number } | null {
  const parts = ref.split(".");
  if (parts.length < 2) return null;
  const chapter = Number(parts[1]);
  if (!Number.isFinite(chapter)) return null;
  return { book: parts[0], chapter };
}

export async function loadBloom31kIndex(): Promise<Bloom31kIndex | null> {
  if (indexCache) return indexCache;
  try {
    const res = await fetch(BLOOM_INDEX_URL, { cache: "force-cache" });
    if (!res.ok) return null;
    indexCache = (await res.json()) as Bloom31kIndex;
    return indexCache;
  } catch {
    return null;
  }
}

export async function loadBloomChapterShard(
  book: string,
  chapter: number,
): Promise<BloomChapterShard | null> {
  const shardId = `${book}.${chapter}`;
  if (shardCache.has(shardId)) return shardCache.get(shardId) ?? null;
  try {
    const res = await fetch(`${BLOOM_SHARD_BASE}/${shardId}.json`, { cache: "force-cache" });
    if (!res.ok) return null;
    const doc = (await res.json()) as BloomChapterShard;
    shardCache.set(shardId, doc);
    return doc;
  } catch {
    return null;
  }
}

/** Secondary fetch: canon chapter verse list when showroom graph slice is thin. */
export async function bloomSecondaryVerseRefsForRef(ref: string): Promise<string[]> {
  const parsed = parseRef(ref);
  if (!parsed) return [];
  const shard = await loadBloomChapterShard(parsed.book, parsed.chapter);
  return shard?.verse_refs ?? [];
}

export async function bloomSecondaryRefsForQueryHints(
  query: string,
  baseRefs: string[],
  maxExtra = 24,
): Promise<string[]> {
  const index = await loadBloom31kIndex();
  if (!index?.chapter_shards?.length) return baseRefs;

  const seen = new Set(baseRefs);
  const out = [...baseRefs];
  const q = query.toLowerCase();

  for (const row of index.chapter_shards) {
    if (out.length - baseRefs.length >= maxExtra) break;
    const book = row.book;
    if (!q.includes(book.toLowerCase()) && !q.includes(row.shard_id.toLowerCase())) continue;
    const shard = await loadBloomChapterShard(book, row.chapter);
    if (!shard?.verse_refs) continue;
    for (const r of shard.verse_refs) {
      if (seen.has(r)) continue;
      seen.add(r);
      out.push(r);
      if (out.length - baseRefs.length >= maxExtra) break;
    }
  }
  return out;
}

export function bloomCoverageLabelKo(extraCount: number): string {
  if (extraCount <= 0) return "";
  return `[HYPO] 31k bloom secondary +${extraCount}절 (쇼룸 슬라이스 보조)`;
}
