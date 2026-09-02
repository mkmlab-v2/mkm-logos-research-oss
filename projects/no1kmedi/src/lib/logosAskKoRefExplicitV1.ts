/**
 * Korean explicit verse cite parser — 「창세기 9장 4절」→ Gen.9.4
 * research_only · [NON_GATING] · send_gate HOLD · matching≠interpretation
 */
export type KoRefExplicitHitV1 = {
  refs: string[];
  book_osis: string;
  chapter: number;
  verse: number | null;
  raw_span: string;
};

const BOOK_MAP: Array<{ re: RegExp; osis: string }> = [
  { re: /창세기|genesis|gen\.?/i, osis: "Gen" },
  { re: /출애굽기|출애굽|exodus|exod\.?/i, osis: "Exod" },
  { re: /레위기|leviticus|lev\.?/i, osis: "Lev" },
  { re: /민수기|numbers|num\.?/i, osis: "Num" },
  { re: /신명기|deuteronomy|deut\.?/i, osis: "Deut" },
  { re: /시편|psalms?|ps\.?/i, osis: "Ps" },
  { re: /잠언|proverbs|prov\.?/i, osis: "Prov" },
  { re: /이사야|isaiah|isa\.?/i, osis: "Isa" },
  { re: /마태복음|마태|matthew|matt\.?/i, osis: "Matt" },
  { re: /마가복음|마가|mark\.?/i, osis: "Mark" },
  { re: /누가복음|누가|luke\.?/i, osis: "Luke" },
  { re: /요한복음|요한(?!\s*[일이삼])|john\.?/i, osis: "John" },
  { re: /로마서|romans?|rom\.?/i, osis: "Rom" },
  { re: /히브리서|hebrews|heb\.?/i, osis: "Heb" },
  { re: /요한계시록|계시록|revelation|rev\.?/i, osis: "Rev" },
  { re: /사도행전|acts\.?/i, osis: "Acts" },
  { re: /고린도전서|1\s*corinthians|1cor\.?/i, osis: "1Cor" },
  { re: /고린도후서|2\s*corinthians|2cor\.?/i, osis: "2Cor" },
  { re: /에베소서|ephesians|eph\.?/i, osis: "Eph" },
];

/** 「창세기 9장 4절」·「창 9:4」·「Gen.9.4」 */
const KO_JANG_JEOL_RE =
  /([가-힣A-Za-z.]{2,12})\s*(\d{1,3})\s*장\s*(\d{1,3})\s*절/;
const COLON_RE =
  /([가-힣A-Za-z.]{2,12})\s*(\d{1,3})\s*[:：.]\s*(\d{1,3})/;

function resolveBook(raw: string): string | null {
  const t = raw.trim();
  for (const b of BOOK_MAP) {
    if (b.re.test(t)) return b.osis;
  }
  return null;
}

export function parseKoRefExplicitV1(query: string): KoRefExplicitHitV1 | null {
  const q = String(query || "").trim();
  if (!q) return null;
  let m = KO_JANG_JEOL_RE.exec(q);
  if (!m) m = COLON_RE.exec(q);
  if (!m) return null;
  const book = resolveBook(m[1]);
  if (!book) return null;
  const chapter = Number(m[2]);
  const verse = Number(m[3]);
  if (!Number.isFinite(chapter) || !Number.isFinite(verse) || chapter < 1 || verse < 1) {
    return null;
  }
  const ref = `${book}.${chapter}.${verse}`;
  return {
    refs: [ref],
    book_osis: book,
    chapter,
    verse,
    raw_span: m[0],
  };
}

export function detectKoRefExplicitV1(query: string): boolean {
  return parseKoRefExplicitV1(query) != null;
}
