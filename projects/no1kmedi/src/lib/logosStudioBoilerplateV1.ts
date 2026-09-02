/** Studio / taxonomy lines that must not surface as Q&A answers or executive summaries. */

const BOILERPLATE_PATTERNS: RegExp[] = [
  /query-time\s*conflict\s*join/i,
  /deterministic\s*synthesis/i,
  /G3\s*hypo(?:\s*idea\s*card)?/i,
  /TSK\s*전량/i,
  /open\s*LLM\s*합성/i,
  /전량\s*TSK\s*교차참조/i,
  /Tier\s*C\s*로드맵/i,
  /큐레이션\s*프리셋·부분\s*그래프/i,
  /query-time\s*GraphRAG·부분\s*그래프/i,
  /Citation-locked evidence/i,
  /query-time\s*GraphRAG/i,
  /query-time/i,
  /bridges=\d+/i,
  /path_id=path_/i,
  /citation lock 구절·경로만/i,
  /디지털\s*환경/i,
  /정보의\s*진실성/i,
  /^lemma bridge\s*—/i,
  /^GraphRAG\s*경로\s*앵커에서\s*lemma/i,
  /GraphRAG\s*보조/i,
  /primary_verse_refs\s*우선/i,
  /stub\s*합선\s*금지/i,
  /^GraphRAG\s*경로/i,
  /신학적\s*단정[·\s]*인과\s*단답\s*없음/i,
  /^신학적\s*단정[·\s]*인과\s*단답/i,
  /인과\s*단답\s*없음\s*\.?\s*$/i,
  /^경로\s*앵커\s*\(citation\s*lock\)/i,
  /^1\.\s*경로\s*앵커/i,
  /주변\s*권·책\s*분포/i,
  /^conflict\s*surface/i,
  /^lemma bridge\s*$/i,
  /^Path envelope/i,
  /orphan\s*veto\s*active/i,
  /^Azure distill\s*·/i,
  /evidence_count/i,
  /학파\s*병렬·citation\s*lock\s*보조\s*입력/i,
  /Track\s*A·실매매·단일\s*해석\s*트리거\s*아님/i,
  /대외\s*송출·상용\s*승격과\s*무관한\s*내부\s*벤치\s*본문/i,
  /citation\s*lock\s*밖\s*stub/i,
  /단일\s*교리·단일\s*인과\s*단답\s*확정\s*없음/i,
  /라우터\s*코사인\s*유사도/i,
  /임계치\s*\(?\s*0\.\d+\s*\)?\s*이하/i,
  /embedding\s*슬라이스/i,
  /GraphRAG\s*dump/i,
  /topic_john_1/i,
  /topic_heb_11/i,
  /Neh[·./\s]*Job/i,
  /Job[·./\s]*Neh/i,
  /citation\s*lock\s*\[HYPO\]/i,
  /soft\s*pack\s*대체/i,
  /generic\s*theology/i,
  /topic-fitness\s*FAIL/i,
  /상고팩/,
  /unmapped\s*HOLD/i,
  /일반팩만/,
];

export function isStudioBoilerplateKo(text: string): boolean {
  const t = (text || "").trim();
  if (!t) return true;
  return BOILERPLATE_PATTERNS.some((re) => re.test(t));
}

export function filterStudioBoilerplateLines(lines: string[]): string[] {
  return lines.filter((line) => !isStudioBoilerplateKo(line));
}
