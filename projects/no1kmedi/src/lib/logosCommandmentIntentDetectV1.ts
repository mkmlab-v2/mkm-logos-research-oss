/** Decalogue / commandment intent detect — research_only · NON_GATING · send_gate HOLD. */

export type DecalogueQueryClassV1 =
  | "decalogue_other_gods_freeform"
  | "decalogue_idols_freeform"
  | "decalogue_name_vain_freeform"
  | "decalogue_sabbath_freeform"
  | "decalogue_honor_parents_freeform"
  | "decalogue_murder_freeform"
  | "decalogue_adultery_freeform"
  | "decalogue_steal_freeform"
  | "decalogue_false_witness_freeform"
  | "decalogue_covet_freeform";

export const DECALOGUE_OTHER_GODS_PRIMARY_REFS = [
  "Exod.20.3",
  "Deut.5.7",
  "Deut.6.14",
  "Josh.24.14",
  "Isa.42.8",
  "1Cor.8.5",
] as const;

export const DECALOGUE_IDOLS_PRIMARY_REFS = [
  "Exod.20.4",
  "Exod.20.5",
  "Deut.5.8",
  "Ps.115.4",
  "Isa.44.9",
  "Acts.17.29",
] as const;

export const DECALOGUE_NAME_VAIN_PRIMARY_REFS = [
  "Exod.20.7",
  "Deut.5.11",
  "Lev.19.12",
  "Matt.5.33",
  "Jas.5.12",
  "Eccl.5.2",
] as const;

export const DECALOGUE_SABBATH_PRIMARY_REFS = [
  "Exod.20.8",
  "Exod.20.9",
  "Deut.5.12",
  "Isa.58.13",
  "Mark.2.27",
  "Heb.4.9",
] as const;

export const DECALOGUE_HONOR_PARENTS_PRIMARY_REFS = [
  "Exod.20.12",
  "Deut.5.16",
  "Eph.6.2",
  "Col.3.20",
  "Prov.23.22",
  "Matt.15.4",
] as const;

export const DECALOGUE_FALSE_WITNESS_PRIMARY_REFS = [
  "Exod.20.16",
  "Deut.5.20",
  "Prov.12.22",
  "Eph.4.25",
  "Matt.19.18",
  "Exod.23.1",
] as const;

export const DECALOGUE_COVET_PRIMARY_REFS = [
  "Exod.20.17",
  "Deut.5.21",
  "Rom.7.7",
  "Rom.13.9",
  "Luke.12.15",
  "Mic.2.2",
] as const;

export const DECALOGUE_ADULTERY_PRIMARY_REFS = [
  "Exod.20.14",
  "Deut.5.18",
  "Matt.5.27",
  "Matt.5.28",
  "Lev.20.10",
  "Prov.6.32",
] as const;

export const DECALOGUE_MURDER_PRIMARY_REFS = [
  "Exod.20.13",
  "Deut.5.17",
  "Matt.5.21",
  "Rom.13.9",
  "Gen.9.6",
] as const;

export const DECALOGUE_STEAL_PRIMARY_REFS = [
  "Exod.20.15",
  "Deut.5.19",
  "Eph.4.28",
  "Lev.19.11",
  "Matt.19.18",
] as const;

const OTHER_GODS_COMMANDMENT_RE =
  /(?:다른|이방)\s*신(?:을|을)?(?:섬기|두|앞)|나\s*외에(?:는)?\s*다른\s*신|우선(?:하지|말)|thou\s*shalt\s*have\s*no\s*other\s*gods|besides\s*me/i;

const IDOLS_COMMANDMENT_RE =
  /우상(?:을|을)?(?:만들|조각|새기)(?:지|지\s*말)?(?:라|라는|의)?|형상(?:을|을)?(?:만들|새기)(?:지|지\s*말)?(?:라|라는|의)?|graven\s*image|idol(?:atry)?|carved\s*image/i;

const NAME_VAIN_COMMANDMENT_RE =
  /(?:여호와|하나님|주)\s*(?:의\s*)?이름(?:을|을)?\s*(?:헛되|허위|거짓|망령)|(?:헛되|허위|거짓|망령)(?:되|이)?(?:게|게)?\s*(?:일컫|부르)|vain(?:ly)?\s*(?:use|take)\s*(?:the\s*)?(?:name|lord)|blasphem/i;

const SABBATH_COMMANDMENT_RE =
  /안식(?:일|일을)?(?:을|을)?(?:기억|지키|거룩)(?:하|하)?(?:라|라는|의)?|sabbath|remember\s*the\s*sabbath|keep\s*(?:it\s*)?holy/i;

const HONOR_PARENTS_COMMANDMENT_RE =
  /부모(?:를|를)?(?:공경|존경|순종)(?:하|하)?(?:라|라는|의)?|honou?r\s*(?:thy|your)\s*(?:father|mother|parents)/i;

const FALSE_WITNESS_COMMANDMENT_RE =
  /거짓\s*(?:증거|말|증언)(?:하지|하)?(?:말|마)?(?:라|라는|의)?|false\s*witness|bear\s*false\s*testimony|perjur/i;

const COVET_COMMANDMENT_RE =
  /탐내(?:지|지\s*말)?(?:라|라는|의)?|covet(?:ing)?|thou\s*shalt\s*not\s*covet|neighbour'?s\s*(?:house|wife)/i;

const ADULTERY_COMMANDMENT_RE =
  /간음(?:하지|하)?(?:말|마)?(?:라|라는|의)?|adulter(?:y|ous)|thou\s*shalt\s*not\s*commit\s*adultery|na'?af|μοιχ|πορνει/i;

const MURDER_COMMANDMENT_RE =
  /살인(?:하지|하)?(?:말|마)?(?:라|라는|의|금지|계명)?|살해|살\s*사람|thou\s*shalt\s*not\s*kill|murder|do\s*not\s*kill|ratsach|φον/i;

const STEAL_COMMANDMENT_RE =
  /도둑질|도둑(?:질)?(?:하지|하)?(?:말|마)?(?:라|라는|의)?|훔치(?:지|지말|지\s*말)?(?:라|라는|의)?|steal(?:ing)?|thou\s*shalt\s*not\s*steal|ganav|κλέπ/i;

const DECALOGUE_FRAME_RE =
  /(?:열)?계명|십계명|율법|돌판|commandment|decalogue|torah/i;

const LAW_BOOK_RE =
  /^(?:Exod|Deut|Matt|Lev|Prov|Rom|Gen|Eph|Josh|Isa|Mark|Col|Luke|Jas|Acts|Mic|Eccl|Heb|Ps)\./i;

const OFFTOPIC_COMMANDMENT_PATH_BOOKS = new Set(["Dan", "Job", "Jer", "Rev"]);

function priorDecalogueRawMatch(query: string, skip: DecalogueQueryClassV1): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  const raw: Array<[DecalogueQueryClassV1, () => boolean]> = [
    [
      "decalogue_other_gods_freeform",
      () =>
        OTHER_GODS_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /다른\s*신|other\s*god/i.test(q)),
    ],
    [
      "decalogue_idols_freeform",
      () =>
        IDOLS_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /우상|형상|idol|graven/i.test(q)),
    ],
    [
      "decalogue_name_vain_freeform",
      () =>
        NAME_VAIN_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /헛되|허위|망령|vain|blasphem/i.test(q)),
    ],
    [
      "decalogue_sabbath_freeform",
      () =>
        SABBATH_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /안식|sabbath/i.test(q)),
    ],
    [
      "decalogue_honor_parents_freeform",
      () =>
        HONOR_PARENTS_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /부모.*(?:공경|존경)|honou?r.*parent/i.test(q)),
    ],
    [
      "decalogue_murder_freeform",
      () =>
        MURDER_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /살인|살\s*사람|murder|kill/i.test(q)),
    ],
    [
      "decalogue_adultery_freeform",
      () =>
        ADULTERY_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /간음|adulter/i.test(q)),
    ],
    [
      "decalogue_steal_freeform",
      () =>
        STEAL_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /도둑|훔치|steal/i.test(q)),
    ],
    [
      "decalogue_false_witness_freeform",
      () =>
        FALSE_WITNESS_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /거짓\s*증|false\s*witness/i.test(q)),
    ],
    [
      "decalogue_covet_freeform",
      () =>
        COVET_COMMANDMENT_RE.test(q) ||
        (DECALOGUE_FRAME_RE.test(q) && /탐내|covet/i.test(q)),
    ],
  ];
  for (const [id, fn] of raw) {
    if (id === skip) return false;
    if (fn()) return true;
  }
  return false;
}

export function detectDecalogueOtherGodsCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (OTHER_GODS_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /다른\s*신|other\s*god/i.test(q)) return true;
  return false;
}

export function detectDecalogueIdolsCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (priorDecalogueRawMatch(q, "decalogue_idols_freeform")) return false;
  if (IDOLS_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /우상|형상|idol|graven/i.test(q)) return true;
  return false;
}

export function detectDecalogueNameVainCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (priorDecalogueRawMatch(q, "decalogue_name_vain_freeform")) return false;
  if (NAME_VAIN_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /헛되|허위|망령|vain|blasphem/i.test(q)) return true;
  return false;
}

export function detectDecalogueSabbathCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (priorDecalogueRawMatch(q, "decalogue_sabbath_freeform")) return false;
  if (SABBATH_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /안식|sabbath/i.test(q)) return true;
  return false;
}

export function detectDecalogueHonorParentsCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (priorDecalogueRawMatch(q, "decalogue_honor_parents_freeform")) return false;
  if (HONOR_PARENTS_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /부모.*(?:공경|존경)|honou?r.*parent/i.test(q)) return true;
  return false;
}

export function detectDecalogueFalseWitnessCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (priorDecalogueRawMatch(q, "decalogue_false_witness_freeform")) return false;
  if (FALSE_WITNESS_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /거짓\s*증|false\s*witness/i.test(q)) return true;
  return false;
}

export function detectDecalogueCovetCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (priorDecalogueRawMatch(q, "decalogue_covet_freeform")) return false;
  if (COVET_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /탐내|covet/i.test(q)) return true;
  return false;
}

export function detectDecalogueAdulteryCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (priorDecalogueRawMatch(q, "decalogue_adultery_freeform")) return false;
  if (ADULTERY_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /간음|adulter/i.test(q)) return true;
  return false;
}

export function detectDecalogueMurderCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (priorDecalogueRawMatch(q, "decalogue_murder_freeform")) return false;
  if (MURDER_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /살인|살\s*사람|murder|kill/i.test(q)) return true;
  return false;
}

export function detectDecalogueStealCommandmentTopic(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  if (priorDecalogueRawMatch(q, "decalogue_steal_freeform")) return false;
  if (STEAL_COMMANDMENT_RE.test(q)) return true;
  if (DECALOGUE_FRAME_RE.test(q) && /도둑|훔치|steal/i.test(q)) return true;
  return false;
}

export function detectDecalogueCommandmentTopic(query: string): boolean {
  return (
    detectDecalogueOtherGodsCommandmentTopic(query) ||
    detectDecalogueIdolsCommandmentTopic(query) ||
    detectDecalogueNameVainCommandmentTopic(query) ||
    detectDecalogueSabbathCommandmentTopic(query) ||
    detectDecalogueHonorParentsCommandmentTopic(query) ||
    detectDecalogueMurderCommandmentTopic(query) ||
    detectDecalogueAdulteryCommandmentTopic(query) ||
    detectDecalogueStealCommandmentTopic(query) ||
    detectDecalogueFalseWitnessCommandmentTopic(query) ||
    detectDecalogueCovetCommandmentTopic(query)
  );
}

export function resolveDecalogueQueryClassV1(query: string): DecalogueQueryClassV1 | null {
  if (detectDecalogueOtherGodsCommandmentTopic(query)) return "decalogue_other_gods_freeform";
  if (detectDecalogueIdolsCommandmentTopic(query)) return "decalogue_idols_freeform";
  if (detectDecalogueNameVainCommandmentTopic(query)) return "decalogue_name_vain_freeform";
  if (detectDecalogueSabbathCommandmentTopic(query)) return "decalogue_sabbath_freeform";
  if (detectDecalogueHonorParentsCommandmentTopic(query)) return "decalogue_honor_parents_freeform";
  if (detectDecalogueMurderCommandmentTopic(query)) return "decalogue_murder_freeform";
  if (detectDecalogueAdulteryCommandmentTopic(query)) return "decalogue_adultery_freeform";
  if (detectDecalogueStealCommandmentTopic(query)) return "decalogue_steal_freeform";
  if (detectDecalogueFalseWitnessCommandmentTopic(query)) return "decalogue_false_witness_freeform";
  if (detectDecalogueCovetCommandmentTopic(query)) return "decalogue_covet_freeform";
  return null;
}

export function resolveDecalogueAdulteryPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_ADULTERY_PRIMARY_REFS];
}

export function resolveDecalogueMurderPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_MURDER_PRIMARY_REFS];
}

export function resolveDecalogueStealPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_STEAL_PRIMARY_REFS];
}

export function resolveDecalogueOtherGodsPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_OTHER_GODS_PRIMARY_REFS];
}

export function resolveDecalogueIdolsPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_IDOLS_PRIMARY_REFS];
}

export function resolveDecalogueNameVainPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_NAME_VAIN_PRIMARY_REFS];
}

export function resolveDecalogueSabbathPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_SABBATH_PRIMARY_REFS];
}

export function resolveDecalogueHonorParentsPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_HONOR_PARENTS_PRIMARY_REFS];
}

export function resolveDecalogueFalseWitnessPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_FALSE_WITNESS_PRIMARY_REFS];
}

export function resolveDecalogueCovetPrimaryRefs(_query?: string): string[] {
  void _query;
  return [...DECALOGUE_COVET_PRIMARY_REFS];
}

export function resolveDecaloguePrimaryRefs(
  queryClass: DecalogueQueryClassV1,
  query?: string,
): string[] {
  switch (queryClass) {
    case "decalogue_other_gods_freeform":
      return resolveDecalogueOtherGodsPrimaryRefs(query);
    case "decalogue_idols_freeform":
      return resolveDecalogueIdolsPrimaryRefs(query);
    case "decalogue_name_vain_freeform":
      return resolveDecalogueNameVainPrimaryRefs(query);
    case "decalogue_sabbath_freeform":
      return resolveDecalogueSabbathPrimaryRefs(query);
    case "decalogue_honor_parents_freeform":
      return resolveDecalogueHonorParentsPrimaryRefs(query);
    case "decalogue_murder_freeform":
      return resolveDecalogueMurderPrimaryRefs(query);
    case "decalogue_adultery_freeform":
      return resolveDecalogueAdulteryPrimaryRefs(query);
    case "decalogue_steal_freeform":
      return resolveDecalogueStealPrimaryRefs(query);
    case "decalogue_false_witness_freeform":
      return resolveDecalogueFalseWitnessPrimaryRefs(query);
    case "decalogue_covet_freeform":
      return resolveDecalogueCovetPrimaryRefs(query);
    default:
      return [];
  }
}

export function hasDecalogueAdulteryEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.(13|14|15)\b/i.test(norm)) return true;
    if (/^Deut\.5\.(17|18|19)\b/i.test(norm)) return true;
    if (/^Matt\.5\.(27|28|29|30)\b/i.test(norm)) return true;
    if (/^Lev\.20\.10\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueMurderEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.13\b/i.test(norm)) return true;
    if (/^Deut\.5\.17\b/i.test(norm)) return true;
    if (/^Matt\.5\.(21|22)\b/i.test(norm)) return true;
    if (/^Rom\.13\.9\b/i.test(norm)) return true;
    if (/^Gen\.9\.6\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueStealEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.15\b/i.test(norm)) return true;
    if (/^Deut\.5\.19\b/i.test(norm)) return true;
    if (/^Eph\.4\.28\b/i.test(norm)) return true;
    if (/^Lev\.19\.11\b/i.test(norm)) return true;
    if (/^Matt\.19\.18\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueOtherGodsEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.3\b/i.test(norm)) return true;
    if (/^Deut\.5\.7\b/i.test(norm)) return true;
    if (/^Deut\.6\.14\b/i.test(norm)) return true;
    if (/^Josh\.24\.14\b/i.test(norm)) return true;
    if (/^Isa\.42\.8\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueIdolsEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.(4|5)\b/i.test(norm)) return true;
    if (/^Deut\.5\.8\b/i.test(norm)) return true;
    if (/^Ps\.115\.4\b/i.test(norm)) return true;
    if (/^Isa\.44\.9\b/i.test(norm)) return true;
    if (/^Acts\.17\.29\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueNameVainEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.7\b/i.test(norm)) return true;
    if (/^Deut\.5\.11\b/i.test(norm)) return true;
    if (/^Lev\.19\.12\b/i.test(norm)) return true;
    if (/^Matt\.5\.33\b/i.test(norm)) return true;
    if (/^Jas\.5\.12\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueSabbathEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.(8|9|10|11)\b/i.test(norm)) return true;
    if (/^Deut\.5\.12\b/i.test(norm)) return true;
    if (/^Isa\.58\.13\b/i.test(norm)) return true;
    if (/^Mark\.2\.27\b/i.test(norm)) return true;
    if (/^Heb\.4\.9\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueHonorParentsEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.12\b/i.test(norm)) return true;
    if (/^Deut\.5\.16\b/i.test(norm)) return true;
    if (/^Eph\.6\.2\b/i.test(norm)) return true;
    if (/^Col\.3\.20\b/i.test(norm)) return true;
    if (/^Prov\.23\.22\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueFalseWitnessEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.16\b/i.test(norm)) return true;
    if (/^Deut\.5\.20\b/i.test(norm)) return true;
    if (/^Prov\.12\.22\b/i.test(norm)) return true;
    if (/^Eph\.4\.25\b/i.test(norm)) return true;
    if (/^Exod\.23\.1\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueCovetEvidence(verseRefs: string[]): boolean {
  return (verseRefs || []).some((ref) => {
    const norm = String(ref || "").replace(/\s/g, "");
    if (/^Exod\.20\.17\b/i.test(norm)) return true;
    if (/^Deut\.5\.21\b/i.test(norm)) return true;
    if (/^Rom\.7\.7\b/i.test(norm)) return true;
    if (/^Rom\.13\.9\b/i.test(norm)) return true;
    if (/^Luke\.12\.15\b/i.test(norm)) return true;
    return false;
  });
}

export function hasDecalogueEvidence(
  queryClass: DecalogueQueryClassV1,
  verseRefs: string[],
): boolean {
  switch (queryClass) {
    case "decalogue_other_gods_freeform":
      return hasDecalogueOtherGodsEvidence(verseRefs);
    case "decalogue_idols_freeform":
      return hasDecalogueIdolsEvidence(verseRefs);
    case "decalogue_name_vain_freeform":
      return hasDecalogueNameVainEvidence(verseRefs);
    case "decalogue_sabbath_freeform":
      return hasDecalogueSabbathEvidence(verseRefs);
    case "decalogue_honor_parents_freeform":
      return hasDecalogueHonorParentsEvidence(verseRefs);
    case "decalogue_murder_freeform":
      return hasDecalogueMurderEvidence(verseRefs);
    case "decalogue_adultery_freeform":
      return hasDecalogueAdulteryEvidence(verseRefs);
    case "decalogue_steal_freeform":
      return hasDecalogueStealEvidence(verseRefs);
    case "decalogue_false_witness_freeform":
      return hasDecalogueFalseWitnessEvidence(verseRefs);
    case "decalogue_covet_freeform":
      return hasDecalogueCovetEvidence(verseRefs);
    default:
      return false;
  }
}

function hasDecalogueLawEvidenceForClass(
  queryClass: DecalogueQueryClassV1,
  verseRefs: string[],
): boolean {
  return hasDecalogueEvidence(queryClass, verseRefs);
}

export function isOfftopicCommandmentPrimaryPath(
  verseRefs: string[],
  queryClass: DecalogueQueryClassV1 = "decalogue_adultery_freeform",
): boolean {
  const refs = verseRefs || [];
  if (!refs.length) return false;
  if (hasDecalogueLawEvidenceForClass(queryClass, refs)) return false;
  const books = refs.map((r) => String(r).split(".")[0] || "");
  const hasLaw = books.some((b) => LAW_BOOK_RE.test(`${b}.`));
  if (hasLaw) return false;
  const offTopicOnly = books.every(
    (b) => OFFTOPIC_COMMANDMENT_PATH_BOOKS.has(b) || b === "Heb" || b === "Jhn" || b === "Luke",
  );
  const danHeavy = books.filter((b) => b === "Dan").length >= 1;
  return offTopicOnly || danHeavy;
}

export function buildDecalogueAdulteryThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueAdulteryPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96);
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `「${qShort}」→ **간음 금지 계명** 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
    "",
    "### 1. 본문 앵커 (citation lock)",
    `${refLine}을 열계명·복음 확장 축의 후보 좌표로 둡니다.`,
    "- **출애굽·신명 (Exod.20.14 · Deut.5.18):** 「네 이웃의 아내를 간음하지 말라」는 언약 공동체·가족·신실함 축의 금지입니다.",
    "- **복음 확장 (Matt.5.27-28):** 예수는 행위뿐 아니라 마음의 간음 욕망까지 확장해 읽는 전통이 있습니다 — 단일 교리 단정은 하지 않습니다.",
    "- **율법·지혜 병렬 (Lev.20.10 · Prov.6.32):** 공동체 규범·지혜 문학에서도 간음은 파괴적 행위 축으로 다루어집니다.",
    "",
    "### 2. 「깊은 의미」 축 (학파 병렬 · 단정 금지)",
    "- **언약·신실:** 배우자·이웃에 대한 신뢰와 언약 충실성을 보호하는 경계로 읽는 전통이 있습니다.",
    "- **욕망·마음:** 복음 전통은 외적 행위를 넘어 마음·시선·욕망까지 다룹니다 — 해석 범위는 학파마다 다릅니다.",
    "- **공동체·정의:** 율법 문맥에서는 가족·재산·명예 질서와 연결된 금지로 읽히기도 합니다.",
    "",
    "### 3. 한계·주의",
    "- 다니엘서·욥기 등 **간음 계명과 직접 무관한 앵커**로 억지 연결하지 않습니다.",
    "- 현대 윤리·가족법·목회 상담 대체가 아닙니다. 교리·법률 확정은 하지 않습니다.",
    "",
    "### 4. 다음 행동 제안",
    "- 「출애굽기 20:14 · 신명기 5:18 · 마태복음 5:27-28 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  ].join("\n");
}

export function buildDecalogueMurderThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueMurderPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96);
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `「${qShort}」→ **살인 금지 계명** 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
    "",
    "### 1. 본문 앵커 (citation lock)",
    `${refLine}을 열계명·복음·창세·로마서 축의 후보 좌표로 둡니다.`,
    "- **출애굽·신명 (Exod.20.13 · Deut.5.17):** 「살인하지 말라」는 생명 존중·공동체 질서 축의 금지입니다.",
    "- **복음 확장 (Matt.5.21-22):** 분노·경멸까지 확장해 읽는 전통이 있습니다 — 단일 교리 단정은 하지 않습니다.",
    "- **창세·로마 (Gen.9.6 · Rom.13:9):** 생명·정의·사랑 명령과 병렬되는 해석 전통이 있습니다.",
    "",
    "### 2. 「깊은 의미」 축 (학파 병렬 · 단정 금지)",
    "- **생명 존중:** 인간 생명의 거룩함·피 흘림 금지로 읽는 전통이 있습니다.",
    "- **분노·마음:** 복음 전통은 외적 살인을 넘어 분노·경멸까지 다룹니다.",
    "- **정의·평화:** 공동체 질서·화해·용서와 연결되는 해석도 있습니다.",
    "",
    "### 3. 한계·주의",
    "- 다니엘서·욥기 등 **살인 계명과 직접 무관한 앵커**로 억지 연결하지 않습니다.",
    "- 전쟁·형벌·자기방어·안락사 등 현대 윤리 대체가 아닙니다.",
    "",
    "### 4. 다음 행동 제안",
    "- 「출애굽기 20:13 · 마태복음 5:21-22 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  ].join("\n");
}

export function buildDecalogueStealThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueStealPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96);
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `「${qShort}」→ **도둑질 금지 계명** 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
    "",
    "### 1. 본문 앵커 (citation lock)",
    `${refLine}을 열계명·복음·에베소·레위 축의 후보 좌표로 둡니다.`,
    "- **출애굽·신명 (Exod.20.15 · Deut.5.19):** 「도둑질하지 말라」는 재산·신뢰·공동체 질서 축의 금지입니다.",
    "- **복음·에베소 (Matt.19.18 · Eph.4.28):** 금지를 넘어 정직한 노동·나눔으로 확장해 읽는 전통이 있습니다.",
    "- **레위 (Lev.19.11):** 거짓·훔침·속임 금지와 병렬됩니다.",
    "",
    "### 2. 「깊은 의미」 축 (학파 병렬 · 단정 금지)",
    "- **재산·신뢰:** 이웃의 소유·공동체 신뢰를 보호하는 경계로 읽힙니다.",
    "- **정직·노동:** 금지를 넘어 정직한 획득·나눔으로 확장하는 해석도 있습니다.",
    "- **공동체·정의:** 가난·억압 맥락과 연결되는 해석 전통도 있으나 단정은 하지 않습니다.",
    "",
    "### 3. 한계·주의",
    "- 다니엘서·욥기 등 **도둑질 계명과 직접 무관한 앵커**로 억지 연결하지 않습니다.",
    "- 현대 재산·세금·지적재산·노동법 대체가 아닙니다.",
    "",
    "### 4. 다음 행동 제안",
    "- 「출애굽기 20:15 · 에베소서 4:28 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  ].join("\n");
}

function buildDecalogueGenericThematicAnswerKo(
  query: string,
  titleKo: string,
  primaryRefs: string[],
  anchorBullets: string[],
  themeBullets: string[],
  limitBullets: string[],
  nextSuggest: string,
): string {
  const qShort = query.trim().slice(0, 96);
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `「${qShort}」→ **${titleKo}** 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
    "",
    "### 1. 본문 앵커 (citation lock)",
    `${refLine}을 열계명·율법·복음 확장 축의 후보 좌표로 둡니다.`,
    ...anchorBullets,
    "",
    "### 2. 「깊은 의미」 축 (학파 병렬 · 단정 금지)",
    ...themeBullets,
    "",
    "### 3. 한계·주의",
    ...limitBullets,
    "",
    "### 4. 다음 행동 제안",
    nextSuggest,
  ].join("\n");
}

export function buildDecalogueOtherGodsThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueOtherGodsPrimaryRefs(query),
): string {
  return buildDecalogueGenericThematicAnswerKo(
    query,
    "다른 신 금지 계명",
    primaryRefs,
    [
      "- **출애굽·신명 (Exod.20.3 · Deut.5.7):** 「나 외에는 다른 신들을 두지 말라」— 독신·언약 충실 축입니다.",
      "- **신명·선지 (Deut.6.14 · Josh.24.14 · Isa.42.8):** 다른 신 섬김 거부·여호와만 경외 언어가 반복됩니다.",
    ],
    [
      "- **독신·언약:** 하나님만 주인으로 두라는 경계로 읽는 전통이 있습니다.",
      "- **이방 종교·우상:** 다른 신과 우상 금지 계명(4-6)과 연결되나 단일 교리 단정은 하지 않습니다.",
    ],
    [
      "- 다니엘서·욥기 등 **본 계명과 직접 무관한 앵커**로 억지 연결하지 않습니다.",
      "- 현대 종교 비교·정치·법률 대체가 아닙니다.",
    ],
    "- 「출애굽기 20:3 · 신명기 5:7 · 이사야 42:8 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  );
}

export function buildDecalogueIdolsThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueIdolsPrimaryRefs(query),
): string {
  return buildDecalogueGenericThematicAnswerKo(
    query,
    "우상 금지 계명",
    primaryRefs,
    [
      "- **출애굽·신명 (Exod.20.4-5 · Deut.5.8):** 「우상을 만들지 말라」— 형상·조각·경배 금지 축입니다.",
      "- **시편·이사야·사도행전 (Ps.115.4 · Isa.44.9 · Acts.17.29):** 우상 무능·창조주와 구별 언어가 병렬입니다.",
    ],
    [
      "- **형상·경배:** 조각·금속·그림 등 형상 숭배 금지로 읽는 전통이 있습니다.",
      "- **마음의 우상:** 외적 형상을 넘어 마음의 탐욕·대체 신으로 확장해 읽기도 합니다.",
    ],
    [
      "- 다니엘서 등 **우상 계명과 직접 무관한 stub**으로 억지 연결하지 않습니다.",
      "- 예술·문화재·고고학 해석 대체가 아닙니다.",
    ],
    "- 「출애굽기 20:4-5 · 시편 115:4 · 이사야 44:9 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  );
}

export function buildDecalogueNameVainThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueNameVainPrimaryRefs(query),
): string {
  return buildDecalogueGenericThematicAnswerKo(
    query,
    "여호와의 이름 헛되이 일컫지 말라",
    primaryRefs,
    [
      "- **출애굽·신명 (Exod.20.7 · Deut.5.11):** 거룩한 이름을 헛되이·거짓되이 부르지 말라는 금지입니다.",
      "- **레위·복음·야고보 (Lev.19.12 · Matt.5.33 · Jas.5.12):** 맹세·거짓 증언과 연결되는 해석 전통이 있습니다.",
    ],
    [
      "- **거룩·경외:** 하나님의 이름을 가볍게 쓰지 말라는 경외 축입니다.",
      "- **맹세·증언:** 거짓 맹세·허위 증언과 병렬되는 해석도 있습니다.",
    ],
    [
      "- 다니엘서 등 **이름 계명과 직접 무관한 stub**으로 억지 연결하지 않습니다.",
      "- 현대 명예훼손·법률 자문 대체가 아닙니다.",
    ],
    "- 「출애굽기 20:7 · 마태복음 5:33 · 야고보서 5:12 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  );
}

export function buildDecalogueSabbathThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueSabbathPrimaryRefs(query),
): string {
  return buildDecalogueGenericThematicAnswerKo(
    query,
    "안식일 기억·지키라",
    primaryRefs,
    [
      "- **출애굽·신명 (Exod.20.8-11 · Deut.5.12):** 안식일을 기억하고 거룩히 지키라는 계명입니다.",
      "- **이사야·복음·히브리 (Isa.58.13 · Mark.2.27 · Heb.4.9):** 안식의 쉼·그리스도·궁극 안식 해석이 병렬입니다.",
    ],
    [
      "- **창조·구속:** 창조 안식과 출애굽 기념으로 읽는 전통이 있습니다.",
      "- **그리스도 안 안식:** 복음 전통은 안식일 규율을 넘어 그리스도 안 쉼으로 확장하기도 합니다.",
    ],
    [
      "- 다니엘서 등 **안식일과 직접 무관한 stub**으로 억지 연결하지 않습니다.",
      "- 현대 노동법·교회 규율·칼endar 논쟁 대체가 아닙니다.",
    ],
    "- 「출애굽기 20:8-11 · 마가복음 2:27 · 히브리서 4:9 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  );
}

export function buildDecalogueHonorParentsThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueHonorParentsPrimaryRefs(query),
): string {
  return buildDecalogueGenericThematicAnswerKo(
    query,
    "부모 공경하라",
    primaryRefs,
    [
      "- **출애굽·신명 (Exod.20.12 · Deut.5.16):** 부모를 공경하라— 장수·복의 약속과 연결되는 유일한 ‘긍정’ 계명으로 읽히기도 합니다.",
      "- **에베소·골로새·잠언 (Eph.6.2 · Col.3.20 · Prov.23.22):** 가정·자녀·부모 존경 언어가 병렬입니다.",
    ],
    [
      "- **공경·순종:** 부모에 대한 존경·돌봄·순종 축으로 읽는 전통이 있습니다.",
      "- **경계·안전:** 학대·방임 맥락은 본문만으로 덮지 않으며 안전·법적 보호와 병행해야 합니다.",
    ],
    [
      "- 다니엘서·욥기 등 **부모 공경과 직접 무관한 stub**으로 억지 연결하지 않습니다.",
      "- 가족 상담·법률·아동 보호 대체가 아닙니다.",
    ],
    "- 「출애굽기 20:12 · 에베소서 6:2 · 잠언 23:22 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  );
}

export function buildDecalogueFalseWitnessThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueFalseWitnessPrimaryRefs(query),
): string {
  return buildDecalogueGenericThematicAnswerKo(
    query,
    "거짓 증거하지 말라",
    primaryRefs,
    [
      "- **출애굽·신명 (Exod.20.16 · Deut.5.20):** 이웃에 대해 거짓 증거하지 말라는 금지입니다.",
      "- **잠언·에베소 (Prov.12.22 · Eph.4.25):** 진실·거짓 입과 공동체 신뢰 언어가 병렬입니다.",
    ],
    [
      "- **진실·정의:** 법정·공동체에서 진실 증언의 중요성으로 읽힙니다.",
      "- **말·평판:** 험담·중상과 연결되는 해석 전통도 있으나 단정은 하지 않습니다.",
    ],
    [
      "- 다니엘서 등 **거짓 증거 계명과 직접 무관한 stub**으로 억지 연결하지 않습니다.",
      "- 법률·소송·언론 자문 대체가 아닙니다.",
    ],
    "- 「출애굽기 20:16 · 잠언 12:22 · 에베소서 4:25 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  );
}

export function buildDecalogueCovetThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDecalogueCovetPrimaryRefs(query),
): string {
  return buildDecalogueGenericThematicAnswerKo(
    query,
    "탐내지 말라",
    primaryRefs,
    [
      "- **출애굽·신명 (Exod.20.17 · Deut.5.21):** 이웃의 집·아내·재산 등을 탐내지 말라는 마음·욕망 금지입니다.",
      "- **로마·누가 (Rom.7.7 · Rom.13.9 · Luke.12.15):** 탐욕·욕망·마음의 죄와 연결되는 해석이 있습니다.",
    ],
    [
      "- **마음·욕망:** 행위 이전 마음의 탐욕을 다루는 계명으로 읽힙니다.",
      "- **만족·청지기:** 탐욕 거부와 만족·나눔으로 확장하는 해석도 병렬입니다.",
    ],
    [
      "- 다니엘서 등 **탐내 계명과 직접 무관한 stub**으로 억지 연결하지 않습니다.",
      "- 재테크·소비·심리 상담 대체가 아닙니다.",
    ],
    "- 「출애굽기 20:17 · 로마서 7:7 · 누가복음 12:15 학파별 해석」처럼 구절을 지정해 재질의해 주세요.",
  );
}

export function buildDecalogueThematicAnswerKo(
  queryClass: DecalogueQueryClassV1,
  query: string,
  primaryRefs?: string[],
): string {
  const refs = primaryRefs ?? resolveDecaloguePrimaryRefs(queryClass, query);
  switch (queryClass) {
    case "decalogue_other_gods_freeform":
      return buildDecalogueOtherGodsThematicAnswerKo(query, refs);
    case "decalogue_idols_freeform":
      return buildDecalogueIdolsThematicAnswerKo(query, refs);
    case "decalogue_name_vain_freeform":
      return buildDecalogueNameVainThematicAnswerKo(query, refs);
    case "decalogue_sabbath_freeform":
      return buildDecalogueSabbathThematicAnswerKo(query, refs);
    case "decalogue_honor_parents_freeform":
      return buildDecalogueHonorParentsThematicAnswerKo(query, refs);
    case "decalogue_murder_freeform":
      return buildDecalogueMurderThematicAnswerKo(query, refs);
    case "decalogue_adultery_freeform":
      return buildDecalogueAdulteryThematicAnswerKo(query, refs);
    case "decalogue_steal_freeform":
      return buildDecalogueStealThematicAnswerKo(query, refs);
    case "decalogue_false_witness_freeform":
      return buildDecalogueFalseWitnessThematicAnswerKo(query, refs);
    case "decalogue_covet_freeform":
      return buildDecalogueCovetThematicAnswerKo(query, refs);
    default:
      return buildDecalogueAdulteryThematicAnswerKo(query, refs);
  }
}
