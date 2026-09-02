/**
 * Logos Ask control-intensity grades G0–G3 (D-CONTROL-GRADE-G0G3-1).
 *
 * Deterministic mapping from existing code signals — NOT an LLM self-score,
 * NOT a hallucination %. Product face for soft-open honesty; send_gate HOLD.
 *
 * Product trust face (`trust_face_ko`) is the human-readable grade that must
 * always match route_band — structural/G0–G3 ids stay in data attrs only.
 * Structural 1.0 ≠ 「자신 있음」; general band never claims curated certainty.
 */

export type LogosAskControlGradeId = "G0" | "G1" | "G2" | "G3";

/** Friend-facing labels — internal ids stay G0–G3 in code/data attrs only. */
export const LOGOS_ASK_CONTROL_GRADE_LABEL_KO: Record<LogosAskControlGradeId, string> = {
  G0: "성경 근거 고정",
  G1: "학파별 비교",
  G2: "참고용 탐구",
  /** Soft-open face — aligned to graded-response strategy G3 「가설·상상」 */
  G3: "가설·상상",
};

/** Product-visible trust face — always show; must match route_band honesty. */
export const LOGOS_ASK_TRUST_FACE_KO: Record<"curated" | "soft" | "general", string> = {
  curated: "근거 강함 · 본문 앵커 분석",
  soft: "참고용 · 신뢰도 보통",
  general: "일반 참고 · 신뢰도 낮음",
};

export const LOGOS_ASK_TRUST_HOLD_LINE_KO = "연구 전용 · 연구 범위 안내" as const;

export const LOGOS_ASK_TRUST_WRONG_PACK_HOLD_KO =
  "연구 범위 안내 · 주제 불일치 가능 — 일반 참고만" as const;

export type LogosAskControlGradeSignalsV1 = {
  preset_id?: string | null;
  query_mode?: string | null;
  citation_strength?: "strong" | "soft" | null;
  honest_control_banner_ko?: string | null;
  /** Confidence-spine route band (curated / soft / general). */
  route_band?: "curated" | "soft" | "general" | null;
  /** Confidence gate reasons — wrong_pack → explicit HOLD face. */
  confidence_reasons?: string[] | null;
};

export type LogosAskControlGradeV1 = {
  id: LogosAskControlGradeId;
  intensity: 0 | 1 | 2 | 3;
  label_ko: string;
  signal_basis: string[];
  /** Honesty stamp: control intensity only — never market as hallucination %. */
  score_kind: "control_intensity";
  not_hallucination_pct: true;
  /** Optional spine band for UI differentiation (honest, not Track A). */
  route_band?: "curated" | "soft" | "general";
  route_band_label_ko?: string;
  /** Always-visible human trust grade (matches route_band; not G0–G3 jargon). */
  trust_face_ko: string;
  /** Always HOLD on this surface — never omit. */
  send_gate_line_ko: typeof LOGOS_ASK_TRUST_HOLD_LINE_KO;
};

const ROUTE_BAND_LABEL_KO: Record<"curated" | "soft" | "general", string> = {
  curated: "근거 강함 · 본문 앵커 분석",
  soft: "참고용 · 신뢰도 보통",
  general: "일반 참고 · 신뢰도 낮음",
};

export function resolveLogosAskTrustFaceKo(opts: {
  route_band?: "curated" | "soft" | "general" | null;
  confidence_reasons?: string[] | null;
  fallback_grade_id?: LogosAskControlGradeId | null;
}): { trust_face_ko: string; route_band: "curated" | "soft" | "general" } {
  const reasons = opts.confidence_reasons ?? [];
  const wrongPack = reasons.some((r) => /wrong_pack/i.test(String(r || "")));
  let band = opts.route_band ?? null;
  if (!band) {
    const gid = (opts.fallback_grade_id ?? "G2").toUpperCase() as LogosAskControlGradeId;
    band = gid === "G0" || gid === "G1" ? "curated" : gid === "G3" ? "general" : "soft";
  }
  if (wrongPack) {
    return { trust_face_ko: LOGOS_ASK_TRUST_WRONG_PACK_HOLD_KO, route_band: "general" };
  }
  return { trust_face_ko: LOGOS_ASK_TRUST_FACE_KO[band], route_band: band };
}

function pack(
  id: LogosAskControlGradeId,
  signal_basis: string[],
  route_band?: "curated" | "soft" | "general",
  confidence_reasons?: string[] | null,
): LogosAskControlGradeV1 {
  const face = resolveLogosAskTrustFaceKo({
    route_band: route_band ?? null,
    confidence_reasons,
    fallback_grade_id: id,
  });
  const out: LogosAskControlGradeV1 = {
    id,
    intensity: Number(id.slice(1)) as 0 | 1 | 2 | 3,
    label_ko: LOGOS_ASK_CONTROL_GRADE_LABEL_KO[id],
    signal_basis: [...signal_basis],
    score_kind: "control_intensity",
    not_hallucination_pct: true,
    trust_face_ko: face.trust_face_ko,
    send_gate_line_ko: LOGOS_ASK_TRUST_HOLD_LINE_KO,
  };
  if (route_band) {
    out.route_band = route_band;
    out.route_band_label_ko = ROUTE_BAND_LABEL_KO[route_band];
  } else {
    out.route_band = face.route_band;
    out.route_band_label_ko = ROUTE_BAND_LABEL_KO[face.route_band];
  }
  return out;
}

/**
 * Map Ask routing / citation signals → G0–G3.
 * Priority: confidence route_band → G3 exploratory freeform → G2 soft/weak → G0 seeded → G1.
 * Always stamps trust_face_ko matching route_band (product-visible; not G-id jargon).
 */
export function mapLogosAskControlGradeG0G3V1(
  signals: LogosAskControlGradeSignalsV1,
): LogosAskControlGradeV1 {
  const preset = (signals.preset_id ?? "").trim();
  const mode = (signals.query_mode ?? "").trim();
  const soft =
    signals.citation_strength === "soft" ||
    Boolean(signals.honest_control_banner_ko?.trim());
  const basis: string[] = [];
  const reasons = signals.confidence_reasons ?? null;
  const modeHas = (token: string) => mode === token || mode.includes(token);
  const band = signals.route_band ?? null;
  const p = (id: LogosAskControlGradeId, rb?: "curated" | "soft" | "general") =>
    pack(id, basis, rb, reasons);

  // Friend-battery pins (before route_band swallow): Job school≠G0 · gematria lookup≠soft G2.
  const isJobSchoolPreset =
    preset === "job_job_suffering_reason" ||
    /job_suffering_reason/.test(preset) ||
    modeHas("inquiry_golden_hub_job_suffering");
  const isGematriaLookupPreset = preset === "dynamic_gematria_lookup";

  // Confidence spine — honest band before narrative-derived grades.
  if (band === "general") {
    basis.push("route_band:general");
    if (mode) basis.push(`query_mode:${mode}`);
    if (preset) basis.push(`preset_id:${preset}`);
    // Gematria meaning/math-original still school-compare face under weak general spine.
    if (isGematriaLookupPreset) return p("G1", "soft");
    // Friend soft-open faith freeform stays G2 (not exploratory G3).
    if (modeHas("inquiry_thematic_faith_freeform")) return p("G2", "soft");
    return p("G3", "general");
  }
  if (band === "soft") {
    basis.push("route_band:soft");
    if (soft) {
      basis.push(
        signals.citation_strength === "soft"
          ? "citation_strength:soft"
          : "honest_control_banner",
      );
    }
    if (mode) basis.push(`query_mode:${mode}`);
    if (preset) basis.push(`preset_id:${preset}`);
    if (isGematriaLookupPreset) return p("G1", "soft");
    if (isJobSchoolPreset) return p("G1", "soft");
    // Bible-code / research theology exploratory stays G3 under soft spine.
    if (
      modeHas("inquiry_thematic_research_theology_freeform") ||
      modeHas("inquiry_thematic_g3_hypo_idea_card")
    ) {
      return p("G3", "general");
    }
    return p("G2", "soft");
  }
  if (band === "curated") {
    basis.push("route_band:curated");
    if (preset) basis.push(`preset_id:${preset}`);
    if (signals.citation_strength === "strong") basis.push("citation_strength:strong");
    // Job hub = school-parallel (G1), not verse-seed G0 (Ps23/topic_*).
    if (isJobSchoolPreset) return p("G1", "curated");
    if (isGematriaLookupPreset) return p("G1", "curated");
    // Friend soft-open faith freeform stays G2 (not citation-lock G0 under curated spine).
    if (modeHas("inquiry_thematic_faith_freeform")) return p("G2", "soft");
    // Gematria freeform ≠ verse-seed G0 (friend battery pin).
    if (modeHas("inquiry_thematic_gematria")) return p("G1", "curated");
    if (/^topic_/.test(preset) || /^book_/.test(preset) || /_anchor$/.test(preset) || modeHas("inquiry_thematic") || modeHas("inquiry_golden_hub")) {
      return p("G0", "curated");
    }
    return p("G1", "curated");
  }

  // G3 — exploratory / hypothesis-first
  // - unmatched → G3 hypo idea card (P0-2; never Deut wrong-pack)
  // - bible-code · research theology freeform
  // Live query_mode may append "+strategy+lemma_bridge" etc. — match by token.
  if (
    modeHas("inquiry_thematic_g3_hypo_idea_card") ||
    preset === "dynamic_g3_hypo_idea_card"
  ) {
    basis.push("query_mode:inquiry_thematic_g3_hypo_idea_card");
    if (preset) basis.push(`preset_id:${preset}`);
    if (soft) {
      basis.push(
        signals.citation_strength === "soft"
          ? "citation_strength:soft"
          : "honest_control_banner",
      );
    }
    return p("G3", "general");
  }
  if (modeHas("inquiry_thematic_research_theology_freeform")) {
    basis.push("query_mode:inquiry_thematic_research_theology_freeform");
    if (soft) {
      basis.push(
        signals.citation_strength === "soft"
          ? "citation_strength:soft"
          : "honest_control_banner",
      );
    }
    if (preset) basis.push(`preset_id:${preset}`);
    return p("G3", "general");
  }

  // G1 — offtopic redirect (before soft→G2): product honesty rules, not exploratory essay
  if (modeHas("inquiry_offtopic_redirect") || preset === "dynamic_offtopic_redirect") {
    if (mode) basis.push(`query_mode:${mode}`);
    if (preset) basis.push(`preset_id:${preset}`);
    return p("G1", "soft");
  }

  // G2 — BIB-DYN pattern primary (soft verse anchors · not prediction)
  if (
    modeHas("inquiry_thematic_bib_dyn_pattern") ||
    preset === "dynamic_bib_dyn_pattern"
  ) {
    if (mode) basis.push(`query_mode:${mode}`);
    if (preset) basis.push(`preset_id:${preset}`);
    if (soft) {
      basis.push(
        signals.citation_strength === "soft"
          ? "citation_strength:soft"
          : "honest_control_banner",
      );
    }
    return p("G2", "soft");
  }

  // G1 — gematria meaning / math-original (before soft→G2 swallow; friend battery pin)
  if (
    isGematriaLookupPreset ||
    modeHas("inquiry_thematic_rev13_gematria") ||
    modeHas("rev13_gematria") ||
    modeHas("inquiry_thematic_gematria")
  ) {
    if (preset) basis.push(`preset_id:${preset}`);
    if (mode) basis.push(`query_mode:${mode}`);
    return p("G1", "soft");
  }

  // G2 — weak citation / soft banner / faith · topical freeform
  if (
    soft ||
    modeHas("inquiry_thematic_faith_freeform") ||
    modeHas("inquiry_thematic_topical_freeform")
  ) {
    if (signals.citation_strength === "soft") basis.push("citation_strength:soft");
    if (signals.honest_control_banner_ko?.trim()) basis.push("honest_control_banner");
    if (mode) basis.push(`query_mode:${mode}`);
    if (preset) basis.push(`preset_id:${preset}`);
    return p("G2", "soft");
  }

  // G0 — seeded verse/hub anchor (topic_/book_/*_anchor) · 본문 고정
  if (/^topic_/.test(preset) || /^book_/.test(preset) || /_anchor$/.test(preset)) {
    basis.push(`preset_id:${preset}`);
    if (signals.citation_strength === "strong") basis.push("citation_strength:strong");
    return p("G0", "curated");
  }

  // G1 — gematria lookup / other dynamic with MKM rules · or curated non-anchor preset
  if (preset === "dynamic_gematria_lookup" || /^dynamic_/.test(preset)) {
    basis.push(`preset_id:${preset}`);
    return p("G1", "soft");
  }

  if (preset) {
    basis.push(`preset_id:${preset}`);
    if (signals.citation_strength === "strong") basis.push("citation_strength:strong");
    return p("G1", "curated");
  }

  basis.push("fallback:unknown_signals");
  return p("G2", "soft");
}
