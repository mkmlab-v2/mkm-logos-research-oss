/** Client-safe S4 public surface filters (no Node imports). */
import { isStudioBoilerplateKo } from "./logosStudioBoilerplateV1";

const GEMATRIA_BULLET_RE =
  /combined_sum|vector_4d|hub_score|state16|Gematria_Pin|topology pin|mispar_/i;

/** Internal pipeline phrases — must never appear in Ring 0 S4 (Done-Product ceiling). */
export const PUBLIC_S4_STUB_PHRASE_RE =
  /Path\s*envelope|orphan\s*veto|concordance\s*pin|citation\s*lock\s*strip|Gematria_Pin|topology\s*pin|lemma:gnosis:|shared_lemma=|Lemma\s*연결\s*이웃\s*구절|envelope\s*concordance|path\s*token\s*preview/i;

export function isPublicS4StubPhrase(text: string): boolean {
  const t = (text || "").trim();
  if (!t || t.length < 8) return true;
  if (GEMATRIA_BULLET_RE.test(t)) return true;
  if (PUBLIC_S4_STUB_PHRASE_RE.test(t)) return true;
  if (isStudioBoilerplateKo(t)) return true;
  return false;
}

export function firstNonStubLine(lines: string[]): string {
  for (const line of lines) {
    const t = line.trim();
    if (t && !isPublicS4StubPhrase(t)) return t;
  }
  return "";
}
