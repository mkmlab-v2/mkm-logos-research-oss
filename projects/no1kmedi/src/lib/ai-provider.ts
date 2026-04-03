/**
 * Pluggable clinical text generation. Wire GEMINI_API_KEY / provider in production.
 * Repository default: deterministic stub so `next build` and smoke routes succeed offline.
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

export async function generateClinicalText(_opts: GenerateClinicalOptions): Promise<GenerateClinicalResult> {
  const configured = !!(process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY)?.trim();
  if (!configured) {
    return {
      text:
        "이 서버에는 생성형 AI 키가 연결되어 있지 않습니다. 운영 환경에서 키·모델 라우팅을 설정해 주세요.",
      provider: "stub",
      fallbackUsed: true,
    };
  }
  return {
    text: "생성형 AI 연동은 배포 환경에서 별도 어댑터로 연결합니다. (placeholder)",
    provider: "placeholder",
    fallbackUsed: true,
  };
}
