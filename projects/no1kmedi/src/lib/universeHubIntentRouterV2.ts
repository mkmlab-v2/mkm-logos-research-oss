import { hubLifeInternalRoute, isMkmlifeEmbedEnabled } from "@/lib/universeHubMkmlifeEmbedV2";
import {
  buildLogosStudioHubRoute,
  questionMatchesLogosCommercial,
} from "@/lib/universeHubLogosCommercialV1";

import { buildMkmlifeAskOneHubDeepLink } from "@/lib/universeHubPluginsV2";



/** Rule-based intent routing — no LLM in hub shell. */

export type HubIntentId =

  | "life"

  | "observe"

  | "developer"

  | "customize"

  | "reports"

  | "clinician";



export type HubIntentChip = {

  id: HubIntentId;

  label: string;

};



export const HUB_INTENT_CHIPS: HubIntentChip[] = [

  { id: "life", label: "라이프·원퀘스천" },

  { id: "observe", label: "관측·리서치" },

  { id: "customize", label: "B2B·가드" },

  { id: "reports", label: "내 리포트" },

  { id: "clinician", label: "한의사 보조" },

  { id: "developer", label: "API·개발" },

];



const OBSERVE_HINTS = ["관측", "오라클", "시장", "코스피", "매크로", "예언"];

const DEV_HINTS = ["api", "압축", "토큰", "개발", "미터링", "sdk"];

const CUSTOMIZE_HINTS = ["b2b", "epb", "페르소나", "맞춤", "가드", "wtt", "엔터프라이즈"];

const REPORTS_HINTS = ["리포트", "보고서", "ledger", "내역"];

const CLINICIAN_HINTS = ["한의사", "진료", "문진", "cdss", "clinician", "한의원"];



export type HubAskValidation =

  | { ok: true }

  | { ok: false; code: "missing_input" };



/** Require at least one of: non-empty question or explicit intent chip. */

export function validateHubAskSubmit(

  question: string,

  selectedIntent: HubIntentId | null,

): HubAskValidation {

  const trimmed = question.trim();

  if (!trimmed && !selectedIntent) {

    return { ok: false, code: "missing_input" };

  }

  return { ok: true };

}



function inferIntentFromQuestion(question: string): HubIntentId {

  const lower = question.toLowerCase();

  if (DEV_HINTS.some((h) => lower.includes(h.toLowerCase()))) {

    return "developer";

  }

  if (OBSERVE_HINTS.some((h) => lower.includes(h) || question.includes(h))) {

    return "observe";

  }

  if (CUSTOMIZE_HINTS.some((h) => lower.includes(h.toLowerCase()) || question.includes(h))) {

    return "customize";

  }

  if (REPORTS_HINTS.some((h) => lower.includes(h.toLowerCase()) || question.includes(h))) {

    return "reports";

  }

  if (CLINICIAN_HINTS.some((h) => lower.includes(h.toLowerCase()) || question.includes(h))) {

    return "clinician";

  }

  return "life";

}



/** Destination URL for ask-bar submit (same-tab navigation). Returns null when validation fails. */

export function resolveHubAskRoute(

  question: string,

  selectedIntent: HubIntentId | null,

): string | null {

  if (!validateHubAskSubmit(question, selectedIntent).ok) {

    return null;

  }



  const trimmed = question.trim();

  if (trimmed && questionMatchesLogosCommercial(trimmed)) {
    return buildLogosStudioHubRoute(trimmed);
  }

  const intent = selectedIntent ?? (trimmed ? inferIntentFromQuestion(trimmed) : "life");

  const hubSource = "source=jema_hub_v2";



  if (intent === "observe") {
    return trimmed
      ? `/hub/oracle?prefill=${encodeURIComponent(trimmed)}&${hubSource}`
      : "/hub/oracle";
  }

  if (intent === "developer") {

    return trimmed

      ? `/hub/developer?prefill=${encodeURIComponent(trimmed)}&${hubSource}`

      : "/hub/developer";

  }

  if (intent === "customize") {

    return trimmed

      ? `/hub/customize?prefill=${encodeURIComponent(trimmed)}&${hubSource}`

      : "/hub/customize";

  }

  if (intent === "reports") {

    return trimmed

      ? `/hub/reports?prefill=${encodeURIComponent(trimmed)}&${hubSource}`

      : "/hub/reports";

  }

  if (intent === "clinician") {

    return trimmed

      ? `/clinician?prefill=${encodeURIComponent(trimmed)}&${hubSource}`

      : "/clinician";

  }



  if (isMkmlifeEmbedEnabled()) {

    return hubLifeInternalRoute(trimmed || undefined);

  }



  if (!trimmed) {
    return buildMkmlifeAskOneHubDeepLink();
  }

  return buildMkmlifeAskOneHubDeepLink({ prefill: trimmed });

}


