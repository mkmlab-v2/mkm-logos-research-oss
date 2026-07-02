/** Runtime freeze manifest + B-track sasang hint for inquiry S2/S3 (Hosted Tier pins). */
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";

import { resolveLogosStudioWorkspaceRoot } from "./logosStudioEmbeddingBridgeV1";
import {
  DEFAULT_FREEZE_LEXICON_META,
  type FreezeLexiconMeta,
} from "./logosInquiryReportV1";

export const FREEZE_MANIFEST_REL =
  "docs/final/artifacts/logos_corpus_knowledge_freeze_manifest_v1_latest.json";

const LEMMA_FLOOR = 290_000;

export type SasangRegimeHintBTrack = {
  schema: "sasang_regime_hint_b_track_v1";
  research_only: true;
  non_gating: true;
  regime_hypothesis: string | null;
  mapping_target: string | null;
  token: string;
  disclaimer_ko: string;
};

export async function loadFreezeLexiconMeta(): Promise<FreezeLexiconMeta> {
  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return DEFAULT_FREEZE_LEXICON_META;

  const filePath = path.join(root, FREEZE_MANIFEST_REL);
  try {
    const raw = await readFile(filePath, "utf8");
    const manifest = JSON.parse(raw) as {
      assets?: {
        lemma_verse_edges_jsonl?: { line_count?: number; min_line_count_floor?: number; sha256?: string };
        sidecar_v2_corpus_full?: { sha256?: string };
      };
    };
    const lemma = manifest.assets?.lemma_verse_edges_jsonl ?? {};
    const sidecar = manifest.assets?.sidecar_v2_corpus_full ?? {};
    const lineCount =
      typeof lemma.line_count === "number" ? lemma.line_count : null;
    const floor =
      typeof lemma.min_line_count_floor === "number"
        ? lemma.min_line_count_floor
        : LEMMA_FLOOR;

    return {
      lemma_edge_line_count: lineCount,
      min_line_count_floor: floor,
      floor_pass: lineCount !== null && lineCount >= floor,
      freeze_manifest_pointer: FREEZE_MANIFEST_REL,
      manifest_sha256: createHash("sha256").update(raw, "utf8").digest("hex"),
      lemma_edges_sha256: String(lemma.sha256 ?? ""),
      sidecar_corpus_sha256: String(sidecar.sha256 ?? ""),
    };
  } catch {
    return DEFAULT_FREEZE_LEXICON_META;
  }
}

export async function loadSasangRegimeHintBTrack(): Promise<SasangRegimeHintBTrack | null> {
  const root = await resolveLogosStudioWorkspaceRoot();
  if (!root) return null;

  const rel = "docs/final/artifacts/sasang_independent_lens_latest.json";
  try {
    const raw = await readFile(path.join(root, rel), "utf8");
    const doc = JSON.parse(raw) as {
      sasang_stream_outputs?: {
        regime_hypothesis?: string;
        mapping_target?: string;
      };
    };
    const stream = doc.sasang_stream_outputs ?? {};
    const hypothesis = stream.regime_hypothesis?.trim() || null;
    const mapping = stream.mapping_target?.trim() || null;
    if (!hypothesis && !mapping) return null;

    return {
      schema: "sasang_regime_hint_b_track_v1",
      research_only: true,
      non_gating: true,
      regime_hypothesis: hypothesis,
      mapping_target: mapping,
      token: `Sasang_Regime:${hypothesis ?? "unknown"}`,
      disclaimer_ko:
        "[HYPO][NON_GATING] B-track 사상 렌즈 토큰만 — 임상·Track A·실매매 트리거 아님.",
    };
  } catch {
    return null;
  }
}
