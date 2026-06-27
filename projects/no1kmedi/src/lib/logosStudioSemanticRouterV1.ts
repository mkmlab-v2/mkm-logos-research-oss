export type LogosStudioLexicalIndex = {
  schema?: string;
  inverted_index?: Array<{ token: string; preset_ids: string[] }>;
  preset_keywords?: Record<string, string[]>;
};

export type LogosStudioEmbeddingIndex = {
  schema?: string;
  backend?: string;
  model_id?: string | null;
  vector_dim?: number;
  min_cosine_threshold?: number;
  vectors?: Array<{ preset_id: string; vector: number[] }>;
};

export function cosineSimilarity(a: number[], b: number[]): number {
  const n = Math.min(a.length, b.length);
  if (n === 0) return 0;
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (let i = 0; i < n; i += 1) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  const denom = Math.sqrt(na) * Math.sqrt(nb);
  return denom > 0 ? dot / denom : 0;
}

export function resolvePresetFromEmbeddingIndex(
  queryVector: number[],
  index: LogosStudioEmbeddingIndex | null | undefined,
): { preset_id: string | null; score: number } {
  const rows = index?.vectors || [];
  if (!rows.length || !queryVector.length) return { preset_id: null, score: 0 };
  const threshold = Number(index?.min_cosine_threshold ?? 0.42);
  let best: { id: string; score: number } | null = null;
  for (const row of rows) {
    const vec = row.vector || [];
    const score = cosineSimilarity(queryVector, vec);
    if (!best || score > best.score) best = { id: row.preset_id, score };
  }
  if (best && best.score >= threshold) return { preset_id: best.id, score: best.score };
  return { preset_id: null, score: best?.score ?? 0 };
}

export function normalizeRouterText(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

export function resolvePresetFromLexicalIndex(
  query: string,
  index: LogosStudioLexicalIndex | null | undefined,
): { preset_id: string | null; score: number } {
  if (!index?.inverted_index?.length) return { preset_id: null, score: 0 };
  const q = normalizeRouterText(query);
  if (!q) return { preset_id: null, score: 0 };

  const scores = new Map<string, number>();
  const tokens = q.split(" ").filter((t) => t.length >= 2);

  for (const entry of index.inverted_index) {
    const token = normalizeRouterText(entry.token);
    if (!token || token.length < 2) continue;
    let hit = false;
    if (q.includes(token)) hit = true;
    else if (tokens.some((t) => token.includes(t) || t.includes(token))) hit = true;
    if (!hit) continue;
    const weight = token.length >= 6 ? 3 : 2;
    for (const pid of entry.preset_ids || []) {
      scores.set(pid, (scores.get(pid) || 0) + weight);
    }
  }

  let best: { id: string; score: number } | null = null;
  for (const [id, score] of scores) {
    if (!best || score > best.score) best = { id, score };
  }
  if (best && best.score >= 2) return { preset_id: best.id, score: best.score };
  return { preset_id: null, score: 0 };
}
