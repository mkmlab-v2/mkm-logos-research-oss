/**
 * Scripture-aware query enrich for Logos Ask — short verse refs pass intake and get research framing.
 * B-track · research_only · display query preserved; pipeline may use enriched text.
 */

const KO_BOOKS =
  "창세기|출애굽기|출애|레위기|민수기|신명기|여호수아|사사기|룻기|사무엘|열왕기|역대|에스라|느헤미야|에스더|욥기|시편|잠언|전도서|아가|이사야|예레미야|에스겔|다니엘|호세아|요엘|아모스|오바댜|요나|미가|나훔|하박국|스바냐|학개|스가랴|말라기|마태|마가|누가|요한|사도행전|로마서|고린도|갈라디아|에베소|빌립보|골로새|데살로니가|디모데|디도서|빌레몬|히브리서|야고보|베드로|유다|요한계시록|계시록";

const EN_BOOKS =
  "Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song of Solomon|Isaiah|Jeremiah|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation";

const SCRIPTURE_ANCHOR_RE = new RegExp(
  [
    `(?:${KO_BOOKS})`,
    `(?:${EN_BOOKS})`,
    String.raw`\b[1-3]?(?:Cor|Tim|Pet|Jn|Jhn|Isa|Ps|Gen|Ex|Lev|Deu|Job|Rom|Mat|Mrk|Luk|Act)\.`,
    String.raw`\d+\s*장`,
    String.raw`\d+\s*[:：]\s*\d+`,
    String.raw`(?:chapter|verse)\s+\d+`,
  ].join("|"),
  "i",
);

const RESEARCH_FRAME_KO =
  " — 학파별 해석 차이·citation lock·lemma 네트워크 관점에서 연구 요약해 달라";

export function hasScriptureAnchor(text: string): boolean {
  const q = (text || "").trim();
  if (!q) return false;
  return SCRIPTURE_ANCHOR_RE.test(q);
}

export function enrichLogosResearchQuery(raw: string): {
  displayQuery: string;
  pipelineQuery: string;
  enriched: boolean;
} {
  const displayQuery = raw.trim();
  if (!displayQuery) {
    return { displayQuery: "", pipelineQuery: "", enriched: false };
  }
  if (displayQuery.length >= 24 || displayQuery.includes(RESEARCH_FRAME_KO.trim())) {
    return { displayQuery, pipelineQuery: displayQuery, enriched: false };
  }
  if (!hasScriptureAnchor(displayQuery)) {
    return { displayQuery, pipelineQuery: displayQuery, enriched: false };
  }
  return {
    displayQuery,
    pipelineQuery: `${displayQuery}${RESEARCH_FRAME_KO}`,
    enriched: true,
  };
}

/** Intake min length — scripture anchors may be shorter than generic 12-char floor. */
export function logosResearchQuestionMinChars(question: string): number {
  return hasScriptureAnchor(question) ? 4 : 12;
}
