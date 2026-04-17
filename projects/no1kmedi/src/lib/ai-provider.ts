/**
 * Pluggable clinical text generation via OpenRouter (OpenAI-compatible).
 * Falls back to deterministic stub when API key is unavailable or upstream fails.
 */
export type GenerateClinicalOptions = {
  prompt: string;
  systemInstruction: string;
  model?: string;
  temperature?: number;
  maxOutputTokens?: number;
  topP?: number;
  topK?: number;
};

export type GenerateClinicalResult = {
  text: string;
  provider: string;
  fallbackUsed: boolean;
};

type OpenRouterResponse = {
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

export async function generateClinicalText(opts: GenerateClinicalOptions): Promise<GenerateClinicalResult> {
  const apiKey = getOpenRouterApiKey();
  if (!apiKey) {
    return {
      text:
        "이 서버에는 생성형 AI 키가 연결되어 있지 않습니다. 운영 환경에서 키·모델 라우팅을 설정해 주세요.",
      provider: "stub",
      fallbackUsed: true,
    };
  }

  const model = toOpenRouterModel(opts.model);
  const endpoint = (process.env.OPENROUTER_BASE_URL?.trim() || "https://openrouter.ai/api/v1").replace(/\/$/, "") + "/chat/completions";
  const body = {
    model,
    messages: [
      {
        role: "system",
        content: opts.systemInstruction,
      },
      {
        role: "user",
        content: opts.prompt,
      },
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
        "HTTP-Referer": process.env.OPENROUTER_HTTP_REFERER?.trim() || "https://no1kmedi.local",
        "X-Title": process.env.OPENROUTER_APP_NAME?.trim() || "no1kmedi-web",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!res.ok) {
      return buildFallback(`AI 응답 준비 중입니다. (${res.status}) 기본 상담 안내를 먼저 진행해드릴게요.`);
    }
    const data = (await res.json()) as OpenRouterResponse;
    const text = data.choices?.[0]?.message?.content?.trim();
    if (!text) {
      return buildFallback();
    }
    return {
      text,
      provider: `openrouter:${model}`,
      fallbackUsed: false,
    };
  } catch {
    return buildFallback();
  }
}
