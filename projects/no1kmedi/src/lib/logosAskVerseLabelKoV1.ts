/**
 * KO UI verse labels — Korean book names primary; OSIS/EN secondary (tooltip).
 * Display only · research_only · ≠ doctrine lock.
 */

const BOOK_KO: Record<string, string> = {
  Gen: "창세기",
  Genesis: "창세기",
  Exod: "출애굽기",
  Ex: "출애굽기",
  Exodus: "출애굽기",
  Lev: "레위기",
  Leviticus: "레위기",
  Num: "민수기",
  Numbers: "민수기",
  Deut: "신명기",
  Deuteronomy: "신명기",
  Josh: "여호수아",
  Joshua: "여호수아",
  Judg: "사사기",
  Judges: "사사기",
  Ruth: "룻기",
  "1Sam": "사무엘상",
  "2Sam": "사무엘하",
  "1Kgs": "열왕기상",
  "2Kgs": "열왕기하",
  "1Chr": "역대상",
  "2Chr": "역대하",
  Ezra: "에스라",
  Neh: "느헤미야",
  Nehemiah: "느헤미야",
  Esth: "에스더",
  Esther: "에스더",
  Job: "욥기",
  Ps: "시편",
  Psalm: "시편",
  Psalms: "시편",
  Prov: "잠언",
  Proverbs: "잠언",
  Eccl: "전도서",
  Ecclesiastes: "전도서",
  Song: "아가",
  Isa: "이사야",
  Isaiah: "이사야",
  Jer: "예레미야",
  Jeremiah: "예레미야",
  Lam: "예레미야애가",
  Ezek: "에스겔",
  Ezekiel: "에스겔",
  Dan: "다니엘",
  Daniel: "다니엘",
  Hos: "호세아",
  Hosea: "호세아",
  Joel: "요엘",
  Amos: "아모스",
  Obad: "오바댜",
  Jonah: "요나",
  Mic: "미가",
  Micah: "미가",
  Nah: "나훔",
  Hab: "하박국",
  Habakkuk: "하박국",
  Zeph: "스바냐",
  Hag: "학개",
  Zech: "스가랴",
  Zechariah: "스가랴",
  Mal: "말라기",
  Malachi: "말라기",
  Matt: "마태복음",
  Matthew: "마태복음",
  Mark: "마가복음",
  Luke: "누가복음",
  John: "요한복음",
  Jhn: "요한복음",
  Acts: "사도행전",
  Rom: "로마서",
  Romans: "로마서",
  "1Cor": "고린도전서",
  "2Cor": "고린도후서",
  Gal: "갈라디아서",
  Galatians: "갈라디아서",
  Eph: "에베소서",
  Ephesians: "에베소서",
  Phil: "빌립보서",
  Philippians: "빌립보서",
  Col: "골로새서",
  Colossians: "골로새서",
  "1Thess": "데살로니가전서",
  "2Thess": "데살로니가후서",
  "1Tim": "디모데전서",
  "2Tim": "디모데후서",
  Titus: "디도서",
  Phlm: "빌레몬서",
  Heb: "히브리서",
  Hebrews: "히브리서",
  Jas: "야고보서",
  James: "야고보서",
  "1Pet": "베드로전서",
  "2Pet": "베드로후서",
  "1John": "요한일서",
  "2John": "요한이서",
  "3John": "요한삼서",
  Jude: "유다서",
  Rev: "요한계시록",
  Revelation: "요한계시록",
};

/** Prefer short OSIS book keys for shard lookup (John over Matthew-style long forms). */
const BOOK_KO_TO_OSIS: Record<string, string> = {
  창세기: "Gen",
  출애굽기: "Exod",
  레위기: "Lev",
  민수기: "Num",
  신명기: "Deut",
  여호수아: "Josh",
  사사기: "Judg",
  룻기: "Ruth",
  사무엘상: "1Sam",
  사무엘하: "2Sam",
  열왕기상: "1Kgs",
  열왕기하: "2Kgs",
  역대상: "1Chr",
  역대하: "2Chr",
  에스라: "Ezra",
  느헤미야: "Neh",
  에스더: "Esth",
  욥기: "Job",
  시편: "Ps",
  잠언: "Prov",
  전도서: "Eccl",
  아가: "Song",
  이사야: "Isa",
  예레미야: "Jer",
  예레미야애가: "Lam",
  에스겔: "Ezek",
  다니엘: "Dan",
  호세아: "Hos",
  요엘: "Joel",
  아모스: "Amos",
  오바댜: "Obad",
  요나: "Jonah",
  미가: "Mic",
  나훔: "Nah",
  하박국: "Hab",
  스바냐: "Zeph",
  학개: "Hag",
  스가랴: "Zech",
  말라기: "Mal",
  마태복음: "Matt",
  마가복음: "Mark",
  누가복음: "Luke",
  요한복음: "John",
  사도행전: "Acts",
  로마서: "Rom",
  고린도전서: "1Cor",
  고린도후서: "2Cor",
  갈라디아서: "Gal",
  에베소서: "Eph",
  빌립보서: "Phil",
  골로새서: "Col",
  데살로니가전서: "1Thess",
  데살로니가후서: "2Thess",
  디모데전서: "1Tim",
  디모데후서: "2Tim",
  디도서: "Titus",
  빌레몬서: "Phlm",
  히브리서: "Heb",
  야고보서: "Jas",
  베드로전서: "1Pet",
  베드로후서: "2Pet",
  요한일서: "1John",
  요한이서: "2John",
  요한삼서: "3John",
  유다서: "Jude",
  요한계시록: "Rev",
  계시록: "Rev",
};

/**
 * Format OSIS-like `John.11.25` → `요한복음 11:25` (KO UI default).
 * Falls back to original ref when book unknown.
 */
export function formatVerseRefKoV1(ref: string): string {
  const raw = String(ref || "").trim();
  if (!raw) return "";
  const m = /^([1-3]?\s*[A-Za-z]+)\.(\d+)(?:\.(\d+))?$/i.exec(raw.replace(/\s+/g, ""));
  if (!m) return raw;
  const bookKey = m[1].replace(/\s+/g, "");
  const ko = BOOK_KO[bookKey] || BOOK_KO[bookKey.replace(/^[a-z]/, (c) => c.toUpperCase())];
  if (!ko) return raw;
  const ch = m[2];
  const vs = m[3];
  return vs ? `${ko} ${ch}:${vs}` : `${ko} ${ch}장`;
}

/**
 * Parse KO display label (`요한복음 11:25` / `히브리서 11장`) → OSIS-like key.
 * Display reverse only · research_only · ≠ doctrine lock.
 */
export function parseVerseRefKoToOsisV1(label: string): string | null {
  const raw = String(label || "").trim();
  if (!raw) return null;
  const m =
    /^(창세기|출애굽기|레위기|민수기|신명기|여호수아|사사기|룻기|사무엘상|사무엘하|열왕기상|열왕기하|역대상|역대하|에스라|느헤미야|에스더|욥기|시편|잠언|전도서|아가|이사야|예레미야애가|예레미야|에스겔|다니엘|호세아|요엘|아모스|오바댜|요나|미가|나훔|하박국|스바냐|학개|스가랴|말라기|마태복음|마가복음|누가복음|요한복음|사도행전|로마서|고린도전서|고린도후서|갈라디아서|에베소서|빌립보서|골로새서|데살로니가전서|데살로니가후서|디모데전서|디모데후서|디도서|빌레몬서|히브리서|야고보서|베드로전서|베드로후서|요한일서|요한이서|요한삼서|유다서|요한계시록|계시록)\s*(\d{1,3})(?:\s*장)?(?:\s*[:：]\s*(\d{1,3}))?$/u.exec(
      raw,
    );
  if (!m) return null;
  const book = BOOK_KO_TO_OSIS[m[1]];
  if (!book) return null;
  const ch = m[2];
  const vs = m[3];
  return vs ? `${book}.${ch}.${vs}` : `${book}.${ch}`;
}

/** Chip label + tooltip pair for KO-primary / EN-secondary display. */
export function verseRefDisplayPairKoV1(ref: string): { label: string; title: string } {
  const raw = String(ref || "").trim();
  const label = formatVerseRefKoV1(raw);
  if (!label || label === raw) {
    return { label: raw, title: `고정 구절 · ${raw}` };
  }
  return { label, title: `${label} · ${raw}` };
}

/**
 * Rewrite OSIS-like tokens inside KO answer prose → Korean book labels.
 * Known books only (formatVerseRefKoV1); unknown tokens left unchanged.
 * Display hygiene · research_only · ≠ doctrine lock.
 */
const OSIS_IN_PROSE_RE =
  /\b([1-3]?[A-Za-z]{2,12})\.(\d{1,3})(?:\.(\d{1,3}))?\b/g;

export function rewriteOsisRefsInProseToKoV1(text: string): string {
  return String(text || "").replace(OSIS_IN_PROSE_RE, (full) => {
    const ko = formatVerseRefKoV1(full);
    return ko && ko !== full ? ko : full;
  });
}
