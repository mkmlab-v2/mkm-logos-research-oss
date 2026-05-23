/**
 * Clinical text generation: Azure OpenAI (startup credits, 1st) + Gemini + OpenRouter + local Ollama.
 * Global: MKM_LLM_PRIORITY (default azure_first when AZURE_OPENAI_* configured).
 * Per-site: JEMA_AI_LLM_PRIORITY, GUARDIAN_CHAT_LLM_PRIORITY.
 */
import {
  azureOpenAiChatCompletionsUrl,
  azureOpenAiDeploymentModel,
  azureOpenAiFetchTimeoutMs,
  getAzureOpenAiConfig,
  isAzureOpenAiConfigured,
  mkmLlmDefaultsToAzureFirst,
  resolveMkmLlmPriorityRaw,
} from "./azure-openai-config";

export type GenerateClinicalOptions = {
  prompt: string;
  systemInstruction: string;
  model?: string;
  temperature?: number;
  maxOutputTokens?: number;
  topP?: number;
  topK?: number;
  siteId?: string;
  feature?: string;
  priorityOverride?: LlmPriority;
};

export type GenerateClinicalResult = {
  text: string;
  provider: string;
  fallbackUsed: boolean;
};

export type LlmPriority =
  | "auto"
  | "azure_first"
  | "azure_only"
  | "gemini_first"
  | "openrouter_first"
  | "local_first"
  | "gemini_only"
  | "openrouter_only"
  | "local_only";

/** Call site for priority resolution (dual lane: guardian Q&A vs everything else). */
export type GenerateClinicalCaller = "default" | "guardian_public_chat";

type OpenAiCompatResponse = {
  choices?: Array<{
    message?: {
      content?: string;
    };
  }>;
};

function getOpenRouterApiKey(): string | null {
  const key = process.env.OPENROUTER_API_KEY?.trim();
  return key || null;
}

function getGeminiApiKey(): string | null {
  const key = process.env.GEMINI_API_KEY?.trim() || process.env.GOOGLE_API_KEY?.trim();
  return key || null;
}

function geminiModel(defaultModel?: string): string {
  const fromEnv = process.env.JEMA_AI_GEMINI_MODEL?.trim() || process.env.GEMINI_MODEL?.trim();
  if (fromEnv) return fromEnv;
  const requested = (defaultModel || "").trim();
  if (requested.startsWith("gemini-")) return requested;
  return "gemini-2.5-flash";
}

/** Ollama: OLLAMA_HOST + /v1/chat/completions — 또는 전체 URL을 LOCAL_LLM_URL에 지정 */
export function deriveLocalLlmUrl(): string {
  const explicit = process.env.LOCAL_LLM_URL?.trim() || "";
  if (explicit) return explicit.replace(/\/$/, "");
  const host = (process.env.OLLAMA_HOST || "").trim().replace(/\/$/, "");
  if (host) return `${host}/v1/chat/completions`;
  return "";
}

export function deriveLocalLlmModel(routeModel?: string): string {
  const fromEnv = process.env.LOCAL_LLM_MODEL?.trim() || process.env.OLLAMA_MODEL?.trim() || "";
  if (fromEnv) return fromEnv;
  const requested = (routeModel || "").trim();
  if (requested && !requested.startsWith("google/") && !requested.includes("gemini")) {
    return requested;
  }
  return "gemma4:e2b";
}

function toOpenRouterModel(model?: string): string {
  const fromEnv = process.env.OPENROUTER_MODEL?.trim();
  if (fromEnv) return fromEnv;
  const requested = (model || "").trim();
  if (!requested) return "google/gemini-2.0-flash-001";
  if (requested.startsWith("google/") || requested.includes("/")) return requested;
  if (requested.startsWith("gemini-")) return `google/${requested}`;
  return "google/gemini-2.0-flash-001";
}

function buildFallback(text?: string): GenerateClinicalResult {
  if (text?.trim()) {
    return { text: text.trim(), provider: "stub", fallbackUsed: true };
  }
  return {
    text: "현재 AI 응답 생성이 지연되고 있습니다. 기본 건강정보를 남겨주시면 한의원 상담 안내로 연결해드리겠습니다.",
    provider: "stub",
    fallbackUsed: true,
  };
}

function parseLlmPriorityValue(raw: string | undefined): LlmPriority | null {
  const p = (raw || "").trim().toLowerCase();
  if (!p) return null;
  if (p === "auto") return "auto";
  if (
    p === "azure_first" ||
    p === "azure_only" ||
    p === "gemini_first" ||
    p === "local_first" ||
    p === "openrouter_first" ||
    p === "gemini_only" ||
    p === "openrouter_only" ||
    p === "local_only"
  ) {
    return p;
  }
  return null;
}

function defaultLlmPriority(): LlmPriority {
  if (mkmLlmDefaultsToAzureFirst()) return "azure_first";
  return "auto";
}

function llmPriority(): LlmPriority {
  return parseLlmPriorityValue(resolveMkmLlmPriorityRaw()) || defaultLlmPriority();
}

/** Effective priority for generateClinicalText second argument. */
export function resolveLlmPriorityForCaller(caller: GenerateClinicalCaller): LlmPriority {
  if (caller === "default") return llmPriority();
  const explicit = parseLlmPriorityValue(process.env.GUARDIAN_CHAT_LLM_PRIORITY);
  if (explicit) return explicit;
  return llmPriority();
}

function localTimeoutMs(): number {
  const v = parseInt(process.env.LOCAL_LLM_TIMEOUT_MS || process.env.LOCAL_LLM_FETCH_TIMEOUT_MS || "", 10);
  if (Number.isFinite(v) && v >= 3000) return Math.min(v, 600000);
  return 120000;
}

async function fetchAzureOpenAi(opts: GenerateClinicalOptions): Promise<GenerateClinicalResult> {
  const cfg = getAzureOpenAiConfig();
  if (!cfg) {
    return buildFallback("Azure OpenAI가 설정되어 있지 않습니다.");
  }
  const model = azureOpenAiDeploymentModel(cfg);
  const url = azureOpenAiChatCompletionsUrl(cfg);
  const body = {
    model,
    messages: [
      { role: "system", content: opts.systemInstruction },
      { role: "user", content: opts.prompt },
    ],
    temperature: opts.temperature ?? 0.7,
    top_p: opts.topP ?? 0.95,
    max_tokens: opts.maxOutputTokens ?? 1024,
  };
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), azureOpenAiFetchTimeoutMs());
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "api-key": cfg.apiKey,
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) {
      return buildFallback(`Azure OpenAI 응답 준비 중입니다. (${res.status})`);
    }
    const data = (await res.json()) as OpenAiCompatResponse;
    const text = data.choices?.[0]?.message?.content?.trim();
    if (!text) return buildFallback();
    return { text, provider: `azure:${model}`, fallbackUsed: false };
  } catch {
    return buildFallback("Azure OpenAI 호출에 실패했습니다.");
  } finally {
    clearTimeout(t);
  }
}

async function fetchOpenRouter(opts: GenerateClinicalOptions): Promise<GenerateClinicalResult> {
  const apiKey = getOpenRouterApiKey();
  if (!apiKey) {
    return buildFallback();
  }

  const model = toOpenRouterModel(opts.model);
  const endpoint =
    (process.env.OPENROUTER_BASE_URL?.trim() || "https://openrouter.ai/api/v1").replace(/\/$/, "") + "/chat/completions";
  const body = {
    model,
    messages: [
      { role: "system", content: opts.systemInstruction },
      { role: "user", content: opts.prompt },
    ],
    temperature: opts.temperature ?? 0.7,
    top_p: opts.topP ?? 0.95,
    max_tokens: opts.maxOutputTokens ?? 1024,
  };

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
        "HTTP-Referer": process.env.OPENROUTER_HTTP_REFERER?.trim() || "https://jema-ai.com",
        "X-Title": process.env.OPENROUTER_APP_NAME?.trim() || "jema-ai.com",
        "X-MKM-Site-Id": (opts.siteId || "unknown").trim(),
        "X-MKM-Feature": (opts.feature || "clinical_chat").trim(),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!res.ok) {
      return buildFallback(`AI 응답 준비 중입니다. (${res.status}) 기본 상담 안내를 먼저 진행해드릴게요.`);
    }
    const data = (await res.json()) as OpenAiCompatResponse;
    const text = data.choices?.[0]?.message?.content?.trim();
    if (!text) {
      return buildFallback();
    }
    return { text, provider: `openrouter:${model}`, fallbackUsed: false };
  } catch {
    return buildFallback();
  }
}

async function fetchGeminiOpenAiCompatible(opts: GenerateClinicalOptions): Promise<GenerateClinicalResult> {
  const apiKey = getGeminiApiKey();
  if (!apiKey) return buildFallback();
  const endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions";
  const model = geminiModel(opts.model);
  const body = {
    model,
    messages: [
      { role: "system", content: opts.systemInstruction },
      { role: "user", content: opts.prompt },
    ],
    temperature: opts.temperature ?? 0.7,
    top_p: opts.topP ?? 0.95,
    max_tokens: opts.maxOutputTokens ?? 1024,
  };
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!res.ok) {
      return buildFallback(`Gemini 응답 준비 중입니다. (${res.status}) 기본 상담 안내를 먼저 진행해드릴게요.`);
    }
    const data = (await res.json()) as OpenAiCompatResponse;
    const text = data.choices?.[0]?.message?.content?.trim();
    if (!text) return buildFallback();
    return { text, provider: `gemini:${model}`, fallbackUsed: false };
  } catch {
    return buildFallback();
  }
}

async function fetchLocalOpenAiCompatible(opts: GenerateClinicalOptions): Promise<GenerateClinicalResult> {
  const url = deriveLocalLlmUrl();
  if (!url) {
    return {
      text: "로컬 LLM이 설정되어 있지 않습니다. OLLAMA_HOST 또는 LOCAL_LLM_URL, OLLAMA_MODEL(예: gemma4:e2b)을 확인해 주세요.",
      provider: "stub",
      fallbackUsed: true,
    };
  }

  const model = deriveLocalLlmModel(opts.model);
  const body = {
    model,
    messages: [
      { role: "system", content: opts.systemInstruction },
      { role: "user", content: opts.prompt },
    ],
    temperature: opts.temperature ?? 0.7,
    top_p: opts.topP ?? 0.95,
    max_tokens: opts.maxOutputTokens ?? 1024,
  };

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const tok = process.env.LOCAL_LLM_API_KEY?.trim() || process.env.OLLAMA_API_KEY?.trim();
  if (tok) {
    headers.Authorization = `Bearer ${tok}`;
  }

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), localTimeoutMs());

  try {
    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) {
      return buildFallback(`로컬 LLM 응답 오류 (${res.status}). Ollama 실행 및 모델 태그를 확인해 주세요.`);
    }
    const data = (await res.json()) as OpenAiCompatResponse;
    const text = data.choices?.[0]?.message?.content?.trim();
    if (!text) {
      return buildFallback("로컬 LLM이 빈 응답을 반환했습니다.");
    }
    return { text, provider: `local:${model}`, fallbackUsed: false };
  } catch {
    return buildFallback("로컬 LLM 호출에 실패했습니다. Ollama가 떠 있는지와 모델 pull 여부를 확인해 주세요.");
  } finally {
    clearTimeout(t);
  }
}

/** Try backends in order; first non-fallback wins. */
async function chainBackends(
  order: Array<() => Promise<GenerateClinicalResult>>,
): Promise<GenerateClinicalResult> {
  for (const fn of order) {
    const r = await fn();
    if (!r.fallbackUsed) return r;
  }
  return buildFallback();
}

async function generateClinicalTextWithPriority(
  opts: GenerateClinicalOptions,
  p: LlmPriority,
): Promise<GenerateClinicalResult> {
  const key = getOpenRouterApiKey();
  const geminiKey = getGeminiApiKey();
  const localUrl = deriveLocalLlmUrl();
  const azureOk = isAzureOpenAiConfigured();

  if (p === "azure_only") {
    if (!azureOk) {
      return {
        text: "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT을 설정해 주세요.",
        provider: "stub",
        fallbackUsed: true,
      };
    }
    return fetchAzureOpenAi(opts);
  }

  if (p === "local_only") {
    return fetchLocalOpenAiCompatible(opts);
  }

  if (p === "gemini_only") {
    if (!geminiKey) {
      return {
        text: "GEMINI_API_KEY(또는 GOOGLE_API_KEY)가 없습니다. 키를 설정하거나 다른 우선순위를 선택해 주세요.",
        provider: "stub",
        fallbackUsed: true,
      };
    }
    return fetchGeminiOpenAiCompatible(opts);
  }

  if (p === "openrouter_only") {
    if (!key) {
      return {
        text: "OPENROUTER_API_KEY가 없습니다. 키를 설정하거나 JEMA_AI_LLM_PRIORITY=local_only 로컬 모드를 사용해 주세요.",
        provider: "stub",
        fallbackUsed: true,
      };
    }
    return fetchOpenRouter(opts);
  }

  if (p === "azure_first") {
    const order: Array<() => Promise<GenerateClinicalResult>> = [];
    if (azureOk) order.push(() => fetchAzureOpenAi(opts));
    if (geminiKey) order.push(() => fetchGeminiOpenAiCompatible(opts));
    if (key) order.push(() => fetchOpenRouter(opts));
    if (localUrl) order.push(() => fetchLocalOpenAiCompatible(opts));
    if (order.length === 0) {
      return {
        text: "생성형 AI가 연결되어 있지 않습니다. Azure OpenAI 또는 폴백 키를 설정해 주세요.",
        provider: "stub",
        fallbackUsed: true,
      };
    }
    return chainBackends(order);
  }

  if (p === "gemini_first") {
    const order: Array<() => Promise<GenerateClinicalResult>> = [];
    if (geminiKey) order.push(() => fetchGeminiOpenAiCompatible(opts));
    if (key) order.push(() => fetchOpenRouter(opts));
    if (localUrl) order.push(() => fetchLocalOpenAiCompatible(opts));
    if (azureOk) order.push(() => fetchAzureOpenAi(opts));
    return chainBackends(order.length ? order : [async () => buildFallback()]);
  }

  if (p === "local_first") {
    const order: Array<() => Promise<GenerateClinicalResult>> = [];
    if (localUrl) order.push(() => fetchLocalOpenAiCompatible(opts));
    if (azureOk) order.push(() => fetchAzureOpenAi(opts));
    if (key) order.push(() => fetchOpenRouter(opts));
    return chainBackends(order.length ? order : [() => fetchOpenRouter(opts)]);
  }

  if (p === "openrouter_first") {
    const order: Array<() => Promise<GenerateClinicalResult>> = [];
    if (key) order.push(() => fetchOpenRouter(opts));
    if (azureOk) order.push(() => fetchAzureOpenAi(opts));
    if (localUrl) order.push(() => fetchLocalOpenAiCompatible(opts));
    return chainBackends(order.length ? order : [() => fetchLocalOpenAiCompatible(opts)]);
  }

  // auto: Azure(설정 시) → Gemini → OpenRouter → 로컬
  const order: Array<() => Promise<GenerateClinicalResult>> = [];
  if (azureOk) order.push(() => fetchAzureOpenAi(opts));
  if (geminiKey) order.push(() => fetchGeminiOpenAiCompatible(opts));
  if (key) order.push(() => fetchOpenRouter(opts));
  if (localUrl) order.push(() => fetchLocalOpenAiCompatible(opts));
  if (order.length === 0) {
    return {
      text:
        "생성형 AI가 연결되어 있지 않습니다. AZURE_OPENAI_* 또는 GEMINI/OPENROUTER/OLLAMA_HOST를 설정해 주세요.",
      provider: "stub",
      fallbackUsed: true,
    };
  }
  return chainBackends(order);
}

export async function generateClinicalText(
  opts: GenerateClinicalOptions,
  caller: GenerateClinicalCaller = "default",
): Promise<GenerateClinicalResult> {
  return generateClinicalTextWithPriority(opts, opts.priorityOverride || resolveLlmPriorityForCaller(caller));
}
