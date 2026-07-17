/**
 * Category-premise mix hints for Logos Ask — advisory [HYPO][NON_GATING] only.
 * Soft language: possible premise mixing — never "your question is wrong" authority.
 * Client-safe (no Node/fs).
 */

export type CategoryPremiseHintV1 = {
  code: string;
  severity: "advisory";
  hypothesis_tier: "B";
  gating_status: "NON_GATING";
  title_ko: string;
  hint_ko: string;
  suggested_reframe_ko: string;
};

function norm(text: string): string {
  return (text || "").replace(/\s+/g, " ").trim().toLowerCase();
}

function hasMaryLexeme(q: string): boolean {
  return ["마리아", "성모", "maria", "mary", "marian", "mariology", "성모님", "무염시태", "immaculate"].some(
    (m) => q.includes(m),
  );
}

function hasJustificationLexeme(q: string): boolean {
  return [
    "이신칭의",
    "칭의",
    "sola fide",
    "sola-fide",
    "justification by faith",
    "justification",
    "by faith alone",
    "믿음으로 의롭다",
    "믿음으로만",
  ].some((m) => q.includes(m));
}

function hasExplicitCompareIntent(q: string): boolean {
  return /비교|차이|병렬|vs\.?|versus|학파|tradition|해석\s*차|혼재|전제/.test(q);
}

function hasTorahLegalismLexeme(q: string): boolean {
  return ["율법주의", "율법으로 구원", "works righteousness", "율법 준수로", "행위구원"].some((m) =>
    q.includes(m),
  );
}

function hasGraceAloneLexeme(q: string): boolean {
  return ["sola gratia", "은혜만으로", "은총만으로", "grace alone", "오직 은혜"].some((m) =>
    q.includes(m),
  );
}

function hasApocalypticDateLexeme(q: string): boolean {
  return ["종말 날짜", "휴거 날짜", "언제 종말", "날짜 예언", "rapture date", "end times date"].some(
    (m) => q.includes(m),
  );
}

/**
 * Detect high-signal theological category mixes in the user question.
 * Returns at most one primary hint (highest priority first).
 */
export function detectCategoryPremiseHint(query: string): CategoryPremiseHintV1 | null {
  const q = norm(query);
  if (!q || q.length < 4) return null;

  if (hasMaryLexeme(q) && hasJustificationLexeme(q) && !hasExplicitCompareIntent(q)) {
    return {
      code: "mary_mariology_vs_protestant_justification",
      severity: "advisory",
      hypothesis_tier: "B",
      gating_status: "NON_GATING",
      title_ko: "질문 전제 점검 (참고)",
      hint_ko:
        "「이신칭의(Justification by faith)」는 주로 개신교 구원론 용어이고, 전통적 마리아론(Mariology)에서는 칭의보다 은총·순결(예: 무염시태) 축으로 접근하는 경우가 많습니다. 질문 안에 두 범주가 함께 있으면 전제가 혼재되어 있을 수 있습니다.",
      suggested_reframe_ko:
        "예: 「마리아론의 은총·순결 축」과 「개신교 이신칭의」를 학파별로 나눠 비교해 달라 — 라고 물으면 범주가 더 선명해집니다.",
    };
  }

  if (hasTorahLegalismLexeme(q) && hasGraceAloneLexeme(q) && !hasExplicitCompareIntent(q)) {
    return {
      code: "legalism_vs_sola_gratia_mix",
      severity: "advisory",
      hypothesis_tier: "B",
      gating_status: "NON_GATING",
      title_ko: "질문 전제 점검 (참고)",
      hint_ko:
        "「율법주의/행위구원」과 「오직 은혜(sola gratia)」는 서로 다른 구원론 범주입니다. 한 문장에 합치면 전제가 혼재되어 있을 수 있습니다.",
      suggested_reframe_ko:
        "예: 바울서신 기준으로 율법·은혜 관계를 학파 병렬로 정리해 달라 — 라고 물으면 범주가 더 선명해집니다.",
    };
  }

  if (hasApocalypticDateLexeme(q)) {
    return {
      code: "apocalyptic_date_setting_advisory",
      severity: "advisory",
      hypothesis_tier: "B",
      gating_status: "NON_GATING",
      title_ko: "질문 전제 점검 (참고)",
      hint_ko:
        "구체적 종말·휴거 「날짜 확정」은 본 연구 워크스페이스의 교리 판결 범위가 아닙니다. 본문 상징·역사적 해석 전통을 병렬로 읽는 질문으로 바꾸면 더 적합합니다.",
      suggested_reframe_ko:
        "예: 요한계시록 상징을 역사·미래·이상주의 학파로 비교해 달라 — 라고 물으면 연구 축이 맞습니다.",
    };
  }

  return null;
}

export function formatCategoryPremiseHintPublic(hint: CategoryPremiseHintV1): string {
  return `${hint.hint_ko} ${hint.suggested_reframe_ko}`.trim();
}
