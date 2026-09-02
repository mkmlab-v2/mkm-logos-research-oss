/**
 * Declared-section-missing-body gate (advisor FAIL class 선언-미포함).
 * research_only · SEND HOLD · product_all_ok=false · harness≠product
 */
const SECTION_OPEN_RE =
  /(?:이유|관점|해석|스펙트럼|학파|차이|관점\s*이\s*있)[^.。\n]{0,40}(?:있습니다|있나이다|다음과\s*같습니다|아래와\s*같습니다)\s*[.。]?\s*$/u;

const DECLARATIVE_TAIL_RE =
  /(?:몇\s*가지\s*(?:해석적\s*)?관점이\s*있습니다|다음과\s*같습니다|아래와\s*같습니다)\s*[.。]?\s*$/u;

export type DeclaredSectionEvalV1 = {
  ok: boolean;
  failure_class: "declared_section_missing_body" | null;
  last_paragraph: string;
};

export function evaluateDeclaredSectionMissingBodyV1(surface: string): DeclaredSectionEvalV1 {
  const raw = String(surface || "").trim();
  if (!raw) {
    return { ok: false, failure_class: "declared_section_missing_body", last_paragraph: "" };
  }
  const paras = raw
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);
  const last = paras[paras.length - 1] || raw.split(/\n+/).filter(Boolean).pop() || "";
  const compact = last.replace(/\s+/g, " ").trim();
  // Announce-then-stop: last para ends with "관점이 있습니다" style with little body after.
  if (DECLARATIVE_TAIL_RE.test(compact) || SECTION_OPEN_RE.test(compact)) {
    // If last para is only the announcement (short) → fail
    if (compact.length <= 120) {
      return {
        ok: false,
        failure_class: "declared_section_missing_body",
        last_paragraph: compact.slice(0, 200),
      };
    }
  }
  // Also: ends exactly with announcement as final sentence of whole body
  const whole = raw.replace(/\s+/g, " ").trim();
  if (DECLARATIVE_TAIL_RE.test(whole.slice(-80))) {
    return {
      ok: false,
      failure_class: "declared_section_missing_body",
      last_paragraph: whole.slice(-160),
    };
  }
  return { ok: true, failure_class: null, last_paragraph: compact.slice(0, 200) };
}

export const DIVINATION_NT_BRIDGE_REFS = ["Acts.16.16", "Acts.16.18", "Gal.5.20"] as const;

export function mergeDivinationNtBridgeRefs(refs: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const r of [...refs, ...DIVINATION_NT_BRIDGE_REFS]) {
    const t = String(r || "").trim();
    if (!t || seen.has(t)) continue;
    seen.add(t);
    out.push(t);
  }
  return out.slice(0, 10);
}

export function hasDivinationNtBridge(refs: string[]): boolean {
  const set = new Set(refs.map((r) => String(r).trim()));
  return DIVINATION_NT_BRIDGE_REFS.some((r) => set.has(r));
}

/** Append interpretation spectrum + NT bridge when giant cut off mid-promise. */
export function repairDivinationDeclaredSectionAndNtV1(
  query: string,
  body: string,
  verseRefs: string[],
): { body: string; applied: boolean; reasons: string[] } {
  const q = String(query || "");
  const isDiv =
    /점술|사주|관상|타로|복술|divination|tarot|fortune/i.test(q);
  if (!isDiv) return { body, applied: false, reasons: [] };

  const reasons: string[] = [];
  let next = String(body || "");
  const sectionEval = evaluateDeclaredSectionMissingBodyV1(next);
  if (!sectionEval.ok) {
    reasons.push("declared_section_missing_body");
    next = `${next.trim()}\n\n### 해석 관점 (연구 병렬 · 단정 아님)\n- **문자 적용:** 신명기·레위기 금지 목록을 현대 점술·사주·관상·타로에도 직접 적용하는 읽기.\n- **원리 적용:** 고대 신접·복술과 오늘의 상담·점성 상품은 형태가 다르므로, 「다른 영적 원천 의존」원리로만 연결하고 1:1 동일시하지 않는 읽기 [HYPO].\n- 위는 학파 병렬 후보이며 교리·목회 판결이 아닙니다.`;
  }
  if (!hasDivinationNtBridge(verseRefs) && !/Acts\.16|갈\s*5|Gal\.5/i.test(next)) {
    reasons.push("missing_nt_bridge");
    next = `${next.trim()}\n\n### 신약 브리지 (연구 참고)\n- **행 16:16–18:** 점치는 귀신 들린 여종 — 신약도 점술 축을 다룹니다 (Acts.16.16).\n- **갈 5:20:** 육체의 일에 점술(sorcery) 계열이 포함됩니다 (Gal.5.20).\n구약 금지와 신약 서사를 **병렬**로 두고, 단일 교리 단정은 하지 않습니다.`;
  }
  return { body: next, applied: reasons.length > 0, reasons };
}
