/**
 * PersonaDiary on-device STT via Web Speech API [HYPO · Phase 3].
 * Browser-local route only — no vendor billing · max listen cap · no always-on.
 */

export const WEB_SPEECH_MAX_LISTEN_MS = 45_000;
export const WEB_SPEECH_LANG = "ko-KR";
export const WEB_SPEECH_PHASE_3_NOTE_KO =
  "브라우저 내장 음성 인식(ko-KR) · 최대 45초 · 붙여넣기와 동일 Human Gate · 예언·처방 아님";

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((ev: SpeechRecognitionResultEventLike) => void) | null;
  onerror: ((ev: { error: string; message?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type SpeechRecognitionResultEventLike = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [alt: number]: { transcript: string };
    };
  };
};

export type WebSpeechSttCallbacks = {
  onInterim?: (text: string) => void;
  onFinal?: (chunk: string, accumulated: string) => void;
  onError?: (code: string, message: string) => void;
  onEnd?: (durationMs: number, accumulated: string) => void;
};

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function isWebSpeechSttSupported(): boolean {
  return getSpeechRecognitionCtor() !== null;
}

export function startWebSpeechStt(
  callbacks: WebSpeechSttCallbacks,
  options?: { maxListenMs?: number; lang?: string }
): { stop: () => void } | null {
  const Ctor = getSpeechRecognitionCtor();
  if (!Ctor) return null;

  const maxListenMs = options?.maxListenMs ?? WEB_SPEECH_MAX_LISTEN_MS;
  const rec = new Ctor();
  rec.lang = options?.lang ?? WEB_SPEECH_LANG;
  rec.continuous = true;
  rec.interimResults = true;
  rec.maxAlternatives = 1;

  const startedAt = Date.now();
  let accumulated = "";
  let stopped = false;

  const timer = window.setTimeout(() => {
    if (!stopped) {
      stopped = true;
      try {
        rec.stop();
      } catch {
        /* already stopped */
      }
    }
  }, maxListenMs);

  rec.onresult = (ev) => {
    let interim = "";
    for (let i = ev.resultIndex; i < ev.results.length; i += 1) {
      const result = ev.results[i];
      const transcript = (result[0]?.transcript ?? "").trim();
      if (!transcript) continue;
      if (result.isFinal) {
        accumulated = `${accumulated} ${transcript}`.trim();
        callbacks.onFinal?.(transcript, accumulated);
      } else {
        interim = `${interim} ${transcript}`.trim();
      }
    }
    if (interim) {
      callbacks.onInterim?.(`${accumulated} ${interim}`.trim());
    }
  };

  rec.onerror = (ev) => {
    callbacks.onError?.(ev.error, ev.message ?? ev.error);
  };

  rec.onend = () => {
    window.clearTimeout(timer);
    if (!stopped) stopped = true;
    callbacks.onEnd?.(Date.now() - startedAt, accumulated);
  };

  try {
    rec.start();
  } catch (err) {
    window.clearTimeout(timer);
    const msg = err instanceof Error ? err.message : "start_failed";
    callbacks.onError?.("start_failed", msg);
    return null;
  }

  return {
    stop: () => {
      if (stopped) return;
      stopped = true;
      window.clearTimeout(timer);
      try {
        rec.stop();
      } catch {
        try {
          rec.abort();
        } catch {
          /* noop */
        }
      }
    },
  };
}
