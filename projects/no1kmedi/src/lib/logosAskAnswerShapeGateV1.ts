/**
 * Day4 B3/B4/shape evaluators — KO lead · answer shape · verse duplication.
 * research_only · SEND HOLD · ≠ product_all_ok
 */

/** Proper-name / book whitelist — do not count as English dump ratio. */
export const KO_LEAD_PROPER_NAME_WHITELIST = [
  "Genesis",
  "Exodus",
  "Leviticus",
  "Numbers",
  "Deuteronomy",
  "Joshua",
  "Judges",
  "Ruth",
  "Samuel",
  "Kings",
  "Chronicles",
  "Ezra",
  "Nehemiah",
  "Esther",
  "Job",
  "Psalm",
  "Psalms",
  "Proverbs",
  "Ecclesiastes",
  "Isaiah",
  "Jeremiah",
  "Ezekiel",
  "Daniel",
  "Hosea",
  "Joel",
  "Amos",
  "Obadiah",
  "Jonah",
  "Micah",
  "Nahum",
  "Habakkuk",
  "Zephaniah",
  "Haggai",
  "Zechariah",
  "Malachi",
  "Matthew",
  "Mark",
  "Luke",
  "John",
  "Acts",
  "Romans",
  "Corinthians",
  "Galatians",
  "Ephesians",
  "Philippians",
  "Colossians",
  "Thessalonians",
  "Timothy",
  "Titus",
  "Philemon",
  "Hebrews",
  "James",
  "Peter",
  "Jude",
  "Revelation",
  "Gen",
  "Exod",
  "Lev",
  "Num",
  "Deut",
  "Josh",
  "Judg",
  "Ps",
  "Prov",
  "Eccl",
  "Isa",
  "Jer",
  "Ezek",
  "Dan",
  "Hos",
  "Matt",
  "Rom",
  "Cor",
  "Gal",
  "Eph",
  "Phil",
  "Col",
  "Thess",
  "Tim",
  "Heb",
  "Jas",
  "Pet",
  "Rev",
  "Jhn",
  "Nephilim",
  "UFO",
  "Watchers",
  "Enoch",
  "YHWH",
  "Christ",
  "Jesus",
  "Messiah",
] as const;

const COMMANDER_SHAPE_HEADERS = [
  { id: "short", re: /###\s*짧은\s*답/i },
  { id: "grade", re: /###\s*신뢰\s*등급/i },
  { id: "anchors", re: /###\s*근거\s*(본문|구절)/i },
  { id: "paths", re: /###\s*해석\s*갈래/i },
  { id: "limits", re: /###\s*한계/i },
] as const;

const FIVE_SECTION_SHAPE_HEADERS = [
  { id: "short", re: /###\s*핵심\s*주장/i },
  { id: "anchors", re: /###\s*근거\s*구절/i },
  { id: "paths", re: /###\s*반증\s*[·・.]?\s*대안/i },
  { id: "limits", re: /###\s*한계\s*[·・.]?\s*주의/i },
] as const;

const BOOK_ALIAS: Record<string, string> = {
  genesis: "gen",
  gen: "gen",
  창세기: "gen",
  exodus: "exod",
  exod: "exod",
  출애굽기: "exod",
  job: "job",
  욥기: "job",
  욥: "job",
  psalm: "ps",
  psalms: "ps",
  ps: "ps",
  시편: "ps",
  matthew: "matt",
  matt: "matt",
  마태: "matt",
  마태복음: "matt",
  mark: "mark",
  마가: "mark",
  마가복음: "mark",
  luke: "luke",
  누가: "luke",
  누가복음: "luke",
  john: "john",
  jhn: "john",
  요한: "john",
  요한복음: "john",
  revelation: "rev",
  rev: "rev",
  요한계시록: "rev",
  계시록: "rev",
  isaiah: "isa",
  isa: "isa",
  이사야: "isa",
  romans: "rom",
  rom: "rom",
  로마서: "rom",
  corinthians: "cor",
  cor: "cor",
  "1cor": "1cor",
  "2cor": "2cor",
  고린도전서: "1cor",
  고린도후서: "2cor",
  hebrews: "heb",
  heb: "heb",
  히브리서: "heb",
  peter: "pet",
  pet: "pet",
  "1john": "1john",
  "1jhn": "1john",
  "2thess": "2thess",
  thessalonians: "thess",
};

export function hangulCount(text: string): number {
  return (String(text || "").match(/[가-힣]/g) || []).length;
}

export function latinLetterCount(text: string): number {
  return (String(text || "").match(/[A-Za-z]/g) || []).length;
}

/** Strip whitelist proper names before English-ratio measure. */
export function maskProperNamesForEnRatio(text: string): string {
  let t = String(text || "");
  const sorted = [...KO_LEAD_PROPER_NAME_WHITELIST].sort((a, b) => b.length - a.length);
  for (const name of sorted) {
    const re = new RegExp(`\\b${name.replace(/\./g, "\\.")}\\b`, "gi");
    t = t.replace(re, " ");
  }
  // OSIS-ish tokens Book.Chap.Verse
  t = t.replace(
    /\b(?:[1-3]\s*)?[A-Za-z]{2,12}\.\d{1,3}(?:\.\d{1,3}(?:-\d{1,3})?)?\b/g,
    " ",
  );
  return t;
}

export function englishRatioFirstN(text: string, n = 500): number {
  const head = String(text || "").slice(0, n);
  const masked = maskProperNamesForEnRatio(head);
  const en = latinLetterCount(masked);
  const ko = hangulCount(head);
  const denom = en + ko;
  if (denom <= 0) return 0;
  return en / denom;
}

export function firstMeaningfulSentence(text: string): string {
  const lines = String(text || "")
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean)
    .filter((l) => !/^#{1,6}\s/.test(l))
    .filter((l) => !/^[-*•]\s*$/.test(l));
  const first = lines[0] || "";
  if (!first) return "";
  const sent = first.split(/(?<=[.!?。！？])\s+/)[0] || first;
  return sent.trim();
}

export function extractCommanderSection(body: string, titleRe: RegExp): string {
  const t = String(body || "");
  const m = t.match(
    new RegExp(
      `(?:${titleRe.source})\\s*\\n([\\s\\S]*?)(?=\\n###\\s|$)`,
      "i",
    ),
  );
  return (m?.[1] || "").trim();
}

export function isGradeOnlyLead(text: string): boolean {
  const t = String(text || "").trim();
  if (!t) return false;
  return /^(?:일반\s*참고|본문\s*앵커|참고|신뢰도|등급)/.test(t) && hangulCount(t) >= 4;
}

export function isEnglishDumpLead(sentence: string): boolean {
  const s = String(sentence || "").trim();
  if (!s) return true;
  if (hangulCount(s) >= 8) return false;
  if (isGradeOnlyLead(s)) return false;
  const masked = maskProperNamesForEnRatio(s);
  const en = latinLetterCount(masked);
  const ko = hangulCount(s);
  if (en >= 24 && ko < 4) return true;
  if (en >= 40 && ko < 8) return true;
  // School dump: long EN clause without Korean
  if (/Watchers|fallen angels|Second Temple|historical-grammatical|interpretation/i.test(s) && ko < 4) {
    return true;
  }
  return false;
}

export type KoLeadEval = {
  ok: boolean;
  hangul_first_280: number;
  english_ratio_first_500: number;
  first_sentence: string;
  first_sentence_ko: boolean;
  en_dump_first: boolean;
  failures: string[];
};

export function evaluateKoLead(surface: string, opts?: { langEn?: boolean }): KoLeadEval {
  const failures: string[] = [];
  if (opts?.langEn) {
    return {
      ok: true,
      hangul_first_280: hangulCount(surface.slice(0, 280)),
      english_ratio_first_500: englishRatioFirstN(surface, 500),
      first_sentence: firstMeaningfulSentence(surface),
      first_sentence_ko: false,
      en_dump_first: false,
      failures: [],
    };
  }
  const head280 = String(surface || "").slice(0, 280);
  const hangul_first_280 = hangulCount(head280);
  const english_ratio_first_500 = englishRatioFirstN(surface, 500);
  const first_sentence = firstMeaningfulSentence(surface);
  const first_sentence_ko = hangulCount(first_sentence) >= 2;
  const en_dump_first = isEnglishDumpLead(first_sentence);

  // B3 advice: hangul ≥40 in first 280 OR grade-only card
  const hangulOk = hangul_first_280 >= 40 || isGradeOnlyLead(first_sentence);
  if (!hangulOk) failures.push("ko_lead_hangul_lt_40_in_first_280");
  if (!first_sentence_ko && !isGradeOnlyLead(first_sentence)) {
    failures.push("first_meaningful_sentence_not_ko");
  }
  if (en_dump_first) failures.push("en_dump_first");
  // Soft EN ratio on first 500 (whitelist applied)
  if (english_ratio_first_500 > 0.55 && hangul_first_280 < 40) {
    failures.push(`en_ratio_first_500_gt_0.55:${english_ratio_first_500.toFixed(2)}`);
  }

  return {
    ok: failures.length === 0,
    hangul_first_280,
    english_ratio_first_500: Number(english_ratio_first_500.toFixed(3)),
    first_sentence: first_sentence.slice(0, 160),
    first_sentence_ko,
    en_dump_first,
    failures,
  };
}

export type AnswerShapeEval = {
  ok: boolean;
  mode: "commander" | "five_section" | "minimum_short_grade" | "none";
  present: Record<string, boolean>;
  short_nonempty: boolean;
  short_before_grade: boolean;
  failures: string[];
};

export function evaluateAnswerShape(s4Body: string): AnswerShapeEval {
  const body = String(s4Body || "");
  const failures: string[] = [];
  const commanderPresent: Record<string, boolean> = {};
  for (const h of COMMANDER_SHAPE_HEADERS) {
    commanderPresent[h.id] = h.re.test(body);
  }
  const commanderAll = COMMANDER_SHAPE_HEADERS.every((h) => commanderPresent[h.id]);

  if (commanderAll) {
    const shortBody = extractCommanderSection(body, /###\s*짧은\s*답/);
    const short_nonempty = hangulCount(shortBody) >= 8 || shortBody.trim().length >= 12;
    if (!short_nonempty) failures.push("short_answer_empty");
    // Order: short header before grade header
    const iShort = body.search(/###\s*짧은\s*답/i);
    const iGrade = body.search(/###\s*신뢰\s*등급/i);
    const short_before_grade = iShort >= 0 && iGrade > iShort;
    if (!short_before_grade) failures.push("short_not_before_grade");
    return {
      ok: failures.length === 0,
      mode: "commander",
      present: commanderPresent,
      short_nonempty,
      short_before_grade,
      failures,
    };
  }

  const fivePresent: Record<string, boolean> = {};
  for (const h of FIVE_SECTION_SHAPE_HEADERS) {
    fivePresent[h.id] = h.re.test(body);
  }
  const fiveOk =
    fivePresent.short && fivePresent.anchors && fivePresent.paths && fivePresent.limits;
  if (fiveOk) {
    const shortBody = extractCommanderSection(body, /###\s*핵심\s*주장/);
    const short_nonempty = hangulCount(shortBody) >= 8 || shortBody.trim().length >= 12;
    if (!short_nonempty) failures.push("core_claim_empty");
    return {
      ok: failures.length === 0,
      mode: "five_section",
      present: fivePresent,
      short_nonempty,
      short_before_grade: true,
      failures,
    };
  }

  // Documented minimum: short KO lead + grade mention
  const hasGrade = /신뢰\s*등급|일반\s*참고|본문\s*앵커/.test(body);
  const lead = firstMeaningfulSentence(body);
  const minOk = hangulCount(lead) >= 8 && hasGrade;
  if (!minOk) {
    failures.push("shape_minimum_short_plus_grade_missing");
    if (!commanderAll && !fiveOk) failures.push("missing_commander_or_five_section_headers");
  }
  return {
    ok: failures.length === 0 && minOk,
    mode: minOk ? "minimum_short_grade" : "none",
    present: { ...commanderPresent, ...fivePresent },
    short_nonempty: hangulCount(lead) >= 8,
    short_before_grade: true,
    failures,
  };
}

/** Normalize verse ref to canonical key for duplication counting. */
export function normalizeCanonicalVerseRef(raw: string): string | null {
  let t = String(raw || "").trim();
  if (!t || t.length > 48) return null;
  t = t.replace(/\s+/g, " ");
  // Strip trailing punctuation
  t = t.replace(/[),.;]+$/g, "");

  // OSIS Book.Chap.Verse(-Verse)?
  let m = t.match(
    /^(?:([1-3])\s*)?([A-Za-z가-힣]+)\.(\d{1,3})(?:\.(\d{1,3})(?:-(\d{1,3}))?)?$/i,
  );
  if (!m) {
    // Genesis 6:1-4 / 창세기 6:1-4
    m = t.match(
      /^(?:([1-3])\s*)?([A-Za-z가-힣]+)\s+(\d{1,3})(?::(\d{1,3})(?:-(\d{1,3}))?)?$/i,
    );
  }
  if (!m) return null;
  const num = m[1] ? `${m[1]}` : "";
  const bookRaw = `${num}${m[2]}`.toLowerCase().replace(/\s+/g, "");
  const book = BOOK_ALIAS[bookRaw] || BOOK_ALIAS[m[2].toLowerCase()] || bookRaw;
  const chap = m[3];
  const verse = m[4] || "";
  const end = m[5] || "";
  if (verse) {
    return end ? `${book}.${chap}.${verse}-${end}` : `${book}.${chap}.${verse}`;
  }
  return `${book}.${chap}`;
}

const VERSE_REF_EXTRACT_RE =
  /(?:[1-3]\s*)?(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Isaiah|Jeremiah|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation|Gen|Exod|Lev|Num|Deut|Josh|Judg|Ps|Prov|Eccl|Isa|Jer|Ezek|Dan|Hos|Matt|Rom|Cor|Gal|Eph|Phil|Col|Thess|Tim|Heb|Jas|Pet|Rev|Jhn|창세기|출애굽기|레위기|민수기|신명기|여호수아|사사기|룻기|사무엘|열왕|역대|에스라|느헤미야|에스더|욥기|욥|시편|잠언|전도서|이사야|예레미야|에스겔|다니엘|호세아|요엘|아모스|오바댜|요나|미가|나훔|하박국|스바냐|학개|스가랴|말라기|마태복음|마태|마가복음|마가|누가복음|누가|요한복음|요한|사도행전|로마서|고린도|갈라디아|에베소|빌립보|골로새|데살로니가|디모데|디도|빌레몬|히브리서|야고보|베드로|유다|요한계시록|계시록)\.?\s*\d{1,3}(?::\d{1,3}(?:-\d{1,3})?|\.\d{1,3}(?:-\d{1,3})?)?(?!장)/gi;

export function extractNormalizedVerseRefs(text: string): string[] {
  const out: string[] = [];
  for (const m of String(text || "").matchAll(VERSE_REF_EXTRACT_RE)) {
    const key = normalizeCanonicalVerseRef(m[0]);
    if (key) out.push(key);
  }
  return out;
}

export type DuplicationEval = {
  ok: boolean;
  max_count: number;
  offenders: Array<{ ref: string; count: number }>;
  failures: string[];
};

export function evaluateVerseDuplication(
  surface: string,
  opts?: { maxAllowed?: number; comparisonTableMode?: boolean },
): DuplicationEval {
  if (opts?.comparisonTableMode) {
    return { ok: true, max_count: 0, offenders: [], failures: [] };
  }
  const maxAllowed = opts?.maxAllowed ?? 2; // fail at >=3 → allow at most 2
  const refs = extractNormalizedVerseRefs(surface);
  const counts = new Map<string, number>();
  for (const r of refs) {
    counts.set(r, (counts.get(r) || 0) + 1);
  }
  const offenders = [...counts.entries()]
    .filter(([, c]) => c >= maxAllowed + 1)
    .map(([ref, count]) => ({ ref, count }))
    .sort((a, b) => b.count - a.count);
  const max_count = offenders.length ? offenders[0].count : Math.max(0, ...counts.values(), 0);
  const failures = offenders.map((o) => `verse_dup:${o.ref}x${o.count}`);
  return {
    ok: offenders.length === 0,
    max_count,
    offenders: offenders.slice(0, 12),
    failures,
  };
}

export type AnswerShapeGateCaseEval = {
  ko_lead: KoLeadEval;
  shape: AnswerShapeEval;
  duplication: DuplicationEval;
  school_en_dump: boolean;
  ok: boolean;
  failures: string[];
};

export function evaluateSchoolCardsEnDump(schoolTexts: string[]): boolean {
  for (const raw of schoolTexts || []) {
    const t = String(raw || "").trim();
    if (!t) continue;
    if (hangulCount(t) >= 8) continue;
    if (isEnglishDumpLead(t)) return true;
  }
  return false;
}

export function evaluateAnswerShapeGateSurfaces(input: {
  s4Body: string;
  answer?: string;
  verseRefs?: string[];
  schoolInterpretations?: string[];
  langEn?: boolean;
}): AnswerShapeGateCaseEval {
  const s4 = String(input.s4Body || "");
  const answer = String(input.answer || "");
  const schools = input.schoolInterpretations || [];
  const leadSurface = s4 || answer;
  // B4: lead+body only (S4 commander). Path citation list must be unique after public filter.
  const dupSurface = leadSurface;
  const uniquePathRefs: string[] = [];
  const seenPath = new Set<string>();
  for (const raw of input.verseRefs || []) {
    const key = normalizeCanonicalVerseRef(String(raw));
    if (!key) continue;
    if (seenPath.has(key)) continue;
    seenPath.add(key);
    uniquePathRefs.push(String(raw));
  }
  const pathDup = evaluateVerseDuplication(uniquePathRefs.join(" · "), { maxAllowed: 1 });

  const ko_lead = evaluateKoLead(leadSurface, { langEn: input.langEn });
  const shape = evaluateAnswerShape(s4 || answer);
  const duplication = evaluateVerseDuplication(dupSurface);
  const school_en_dump = evaluateSchoolCardsEnDump(schools);

  const failures = [
    ...ko_lead.failures.map((f) => `B3:${f}`),
    ...shape.failures.map((f) => `shape:${f}`),
    ...duplication.failures.map((f) => `B4:${f}`),
  ];
  if (!pathDup.ok) {
    for (const f of pathDup.failures) failures.push(`B4:path_${f}`);
  }
  if (school_en_dump) failures.push("B3:school_card_en_dump");

  return {
    ko_lead,
    shape,
    duplication: {
      ok: duplication.ok && pathDup.ok,
      max_count: Math.max(duplication.max_count, pathDup.max_count),
      offenders: [...duplication.offenders, ...pathDup.offenders].slice(0, 12),
      failures: [...duplication.failures, ...pathDup.failures],
    },
    school_en_dump,
    ok: failures.length === 0,
    failures,
  };
}

const VERSE_REF_IN_LINE_RE =
  /\b(?:[1-3]\s*)?[A-Za-z][A-Za-z0-9]*\.?\s*\d{1,3}(?::\d{1,3}(?:-\d{1,3})?)?/;

/** Drop cite-marker shells after global dedupe removed duplicate refs (T0 thin). */
export function stripEmptyCoreCiteMarkerLines(text: string): string {
  const lines = String(text || "").split("\n");
  const out: string[] = [];
  for (const line of lines) {
    let t = line.trim();
    if (!t) continue;
    if (/핵심\s*근거/.test(t) && !VERSE_REF_IN_LINE_RE.test(t)) {
      const prose = t
        .replace(/핵심\s*근거(?:\([^)]*\))?\s*:?\s*(?:·\s*)+/g, "")
        .replace(/\(보조:\s*(?:·\s*)+\)/g, "")
        .replace(/^[·\s,():]+/, "")
        .trim();
      if (prose.length > 8 && /[가-힣]{4,}/.test(prose)) out.push(prose);
      continue;
    }
    t = t
      .replace(/\(보조:\s*(?:·\s*)+\)/g, "")
      .replace(/핵심\s*근거(?:\([^)]*\))?\s*:\s*·+(?:\s*\(보조:\s*·+\))?/g, "")
      .replace(/·\s*·/g, "·")
      .trim();
    if (t) out.push(t);
  }
  return out.join("\n\n").replace(/\n{3,}/g, "\n\n").trim();
}

/**
 * Latin OSIS-shaped match only (Rev.13.18 / Matt 5:3).
 * Korean prose labels (요한계시록 13:18) must survive dedupe — wiping them leaves
 * 「핵심 앵커는 입니다」 orphans after scrubEvidence maxPerRef=1 (commander paste 20260811t).
 */
export function isLatinOsisShapedVerseMatch(match: string): boolean {
  const t = String(match || "").trim();
  return /^(?:[1-3]\s*)?[A-Za-z][A-Za-z0-9']*(?:\.|\s+)\d/.test(t);
}

/** Restore 「핵심 앵커는 입니다」 if a prior wipe emptied the KO/OSIS label. */
export function repairCoreAnchorOrphanLineV1(text: string): string {
  const raw = String(text || "");
  if (!/핵심\s*앵커는\s*입니다/.test(raw)) return raw;
  const first = raw.match(VERSE_REF_EXTRACT_RE)?.[0]?.trim();
  if (!first) return raw;
  return raw.replace(/핵심\s*앵커는\s*입니다\.?/g, `핵심 앵커는 ${first}입니다.`);
}

/** Dedupe repeated normalized verse refs in prose (keep first N occurrences). */
export function dedupeVerseRefsInProse(text: string, maxPerRef = 1): string {
  const counts = new Map<string, number>();
  const deduped = String(text || "")
    .replace(VERSE_REF_EXTRACT_RE, (match) => {
      const key = normalizeCanonicalVerseRef(match);
      if (!key) return match;
      const n = (counts.get(key) || 0) + 1;
      counts.set(key, n);
      if (n > maxPerRef) {
        // Only blank duplicate Latin OSIS tokens. Keep KO labels in prose
        // (scrubEvidenceAnchorLineFamilyV1 historically targeted OSIS repeats).
        if (!isLatinOsisShapedVerseMatch(match)) return match;
        return "";
      }
      return match;
    })
    // Hang fix: 「마가복음 9:24」 stripped → leave 「은/는/의…」 after colon/bullet/clause.
    .replace(/([:：]\s*)(?:은|는|이|가|의|을|를|도|만)\s+/g, "$1")
    .replace(/(\*\*[^*]+?:\*\*\s*)(?:은|는|이|가|의|을|를|도|만)\s+/g, "$1")
    .replace(/(읽기|비평|전통|축|해석)\s*:\s*(?:은|는|이|가|의|을|를)\s+/g, "$1: ")
    .replace(/([.。!?]|또)\s+(?:은|는|이|가|의)\s+/g, "$1 ")
    // Bare leftover after verse wipe mid-clause: "…읽기: 은 의심" / "…: 의 흔들림"
    .replace(/:\s*(?:은|는|이|가|의)\s+(?=[가-힣])/g, ": ")
    // OSIS wiped at line start: "Rev.13.18을 중심으로" → "을 중심으로"
    .replace(/(^|\n)\s*(?:은|는|이|가|의|을|를|도|만)\s+(?=[가-힣])/g, "$1")
    // KO chapter wipe: "요한계시록 13장 앵커" → "장 앵커" (VERSE_REF matched book+chap before 장)
    .replace(/(^|\n)\s*장\s+(?=앵커|계열|본문|중심)/g, "$1")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\s+([·|,])/g, " $1")
    .replace(/([·|,])\s*([·|,])/g, "$1")
    .replace(/\(\s*\)/g, "")
    .replace(/\(\s*·+\s*/g, "(")
    .replace(/\s*·+\s*\)/g, ")")
    .replace(/\(\s*·+\s*([A-Za-z0-9가-힣])/g, "($1")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  return stripEmptyCoreCiteMarkerLines(repairCoreAnchorOrphanLineV1(deduped));
}
