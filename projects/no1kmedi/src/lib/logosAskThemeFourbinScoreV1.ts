/**
 * Client-side theme-fourbin scorer (mirrors scripts/run_logos_theme_fourbin_parallel_scorecard_v1.py).
 * Meaning-network only — no gematria / vector_4d / address_book merge.
 */

export type ThemeFourbinBinLexV1 = {
  lexemes_en?: string[];
  lexemes_ko?: string[];
  lexemes?: string[];
};

export type ThemeFourbinFramesLexV1 = {
  frame_a?: { bins?: Record<string, ThemeFourbinBinLexV1> };
  frame_b?: { bins?: Record<string, ThemeFourbinBinLexV1> };
};

export type ThemeFourbinScoredFrameV1 = {
  dominant_bin: string;
  bin_weights: Record<string, number>;
  entropy: number;
  spread: number;
};

const LOG4 = Math.log(4);

function collectLexemes(binObj: ThemeFourbinBinLexV1 | undefined): string[] {
  if (!binObj) return [];
  const out: string[] = [];
  for (const key of ["lexemes_en", "lexemes_ko", "lexemes"] as const) {
    const vals = binObj[key];
    if (Array.isArray(vals)) {
      for (const x of vals) {
        const s = String(x || "").trim();
        if (s) out.push(s);
      }
    }
  }
  return out;
}

export function tokenizeThemeFourbin(text: string): Set<string> {
  const t = (text || "").toLowerCase();
  const latin = new Set(
    t
      .split(/[^a-zA-Z0-9_]+/)
      .filter((p) => p.length >= 3),
  );
  const hangul = new Set(t.match(/[\uac00-\ud7a3]{2,}/g) ?? []);
  return new Set([...latin, ...hangul]);
}

function rawBinOverlap(tokens: Set<string>, textLower: string, lexemes: string[]): number {
  let score = 0;
  for (const lex of lexemes) {
    const lx = lex.toLowerCase().trim();
    if (!lx) continue;
    if (tokens.has(lx) || textLower.includes(lx)) score += 1;
  }
  return score;
}

function softmaxNormalize(raw: Record<string, number>, temperature = 1): Record<string, number> {
  const keys = Object.keys(raw);
  if (!keys.length) return {};
  const vals = keys.map((k) => Number(raw[k]) || 0);
  if (vals.every((v) => v <= 0)) {
    const u = 1 / keys.length;
    return Object.fromEntries(keys.map((k) => [k, u]));
  }
  const t = Math.max(temperature, 1e-6);
  const m = Math.max(...vals);
  const exps = vals.map((v) => Math.exp((v - m) / t));
  const s = exps.reduce((a, b) => a + b, 0) || 1;
  return Object.fromEntries(keys.map((k, i) => [k, exps[i] / s]));
}

function entropy(dist: Record<string, number>): number {
  let h = 0;
  for (const p of Object.values(dist)) {
    if (p > 0) h -= p * Math.log(p);
  }
  return h;
}

function spread(dist: Record<string, number>): number {
  const vals = Object.values(dist);
  if (!vals.length) return 0;
  return 1 - Math.max(...vals);
}

function dominantBin(dist: Record<string, number>): string {
  let best = "";
  let bestV = -1;
  for (const [k, v] of Object.entries(dist)) {
    if (v > bestV) {
      bestV = v;
      best = k;
    }
  }
  return best;
}

function scoreOneFrame(
  text: string,
  bins: Record<string, ThemeFourbinBinLexV1> | undefined,
): ThemeFourbinScoredFrameV1 | null {
  if (!bins) return null;
  const binIds = Object.keys(bins);
  if (binIds.length !== 4) return null;
  const tokens = tokenizeThemeFourbin(text);
  const textLower = (text || "").toLowerCase();
  const raw: Record<string, number> = {};
  for (const bid of binIds) {
    raw[bid] = rawBinOverlap(tokens, textLower, collectLexemes(bins[bid]));
  }
  const dist = softmaxNormalize(raw);
  return {
    dominant_bin: dominantBin(dist),
    bin_weights: Object.fromEntries(
      Object.entries(dist).map(([k, v]) => [k, Math.round(v * 1e6) / 1e6]),
    ),
    entropy: Math.round(entropy(dist) * 1e6) / 1e6,
    spread: Math.round(spread(dist) * 1e6) / 1e6,
  };
}

function nearUniform(weights: Record<string, number> | undefined, eps = 0.02): boolean {
  if (!weights) return true;
  return Object.values(weights).every((v) => Math.abs(Number(v) - 0.25) < eps);
}

export function explainAbDifferKoLive(
  rowA: ThemeFourbinScoredFrameV1 | null,
  rowB: ThemeFourbinScoredFrameV1 | null,
): string[] {
  const da = rowA?.dominant_bin || "";
  const db = rowB?.dominant_bin || "";
  const wa = rowA?.bin_weights;
  const wb = rowB?.bin_weights;
  const ua = nearUniform(wa);
  const ub = nearUniform(wb);
  const pa = da && wa ? Number(wa[da] || 0) : 0;
  const pb = db && wb ? Number(wb[db] || 0) : 0;

  if (ua && ub) {
    return [
      "Frame A: 이 표본 어휘로는 4칸이 거의 균등(lex overlap≈0) — 구원사 렌즈에 ‘뚜렷한 한 칸’ 신호가 없음.",
      "Frame B: 역시 거의 균등 — 언약·제도 렌즈도 겹치는 단어가 없어 A/B가 ‘다른 우세축 대결’이 아니라 ‘둘 다 약한 신호’입니다.",
    ];
  }
  const line1 = ua
    ? "Frame A: 구원사 4칸이 거의 균등 — 이 구절 어휘가 creation/fall/redemption/consummation 사전과 거의 안 겹칩니다."
    : `Frame A(구원사 4칸) 우세축=\`${da}\`(비중≈${pa.toFixed(2)}) — 창조→타락→구속→완성 이야기 렌즈로 단어를 셉니다.`;
  const line2 = ub
    ? "Frame B: 약속/법/희생/왕국 4칸이 거의 균등 — 제도 렌즈 사전에 안 잡혀 A와 ‘다른 승자’가 아니라 ‘제도 신호 약함’으로 갈립니다."
    : `Frame B 우세축=\`${db}\`(비중≈${pb.toFixed(2)}) — 같은 구절이라도 렌즈(이야기 vs 제도)가 바뀌면 우세 칸이 달라집니다.`;
  return [line1, line2];
}

/** Score query/answer text into a display block (on-answer / live). */
export function scoreThemeFourbinDisplayLive(
  text: string,
  frames: ThemeFourbinFramesLexV1 | null | undefined,
): {
  frame_a?: ThemeFourbinScoredFrameV1;
  frame_b?: ThemeFourbinScoredFrameV1;
  explain_ab_differ_ko: string[];
  source: "live_score";
} | null {
  const blob = (text || "").trim();
  if (!blob || !frames) return null;
  const fa = scoreOneFrame(blob, frames.frame_a?.bins);
  const fb = scoreOneFrame(blob, frames.frame_b?.bins);
  if (!fa && !fb) return null;
  return {
    frame_a: fa ?? undefined,
    frame_b: fb ?? undefined,
    explain_ab_differ_ko: explainAbDifferKoLive(fa, fb),
    source: "live_score",
  };
}

/** Shape sanity helper — not near-uniform on Frame A. */
export function isFrameANearUniform(weights: Record<string, number> | undefined): boolean {
  return nearUniform(weights);
}

export function frameAEntropyFracOfLog4(entropyVal: number): number {
  return entropyVal / LOG4;
}
