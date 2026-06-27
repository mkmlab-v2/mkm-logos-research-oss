export type PersonadiaryRuntimeSurface = "web_pwa" | "capacitor_webview" | "unknown";

export type ScreenTimeBridgeStatus = {
  status: "unsupported_web" | "stub_pending_native" | "capacitor_detected";
  message_ko: string;
  research_only: true;
};

export const NATIVE_SHELL_HYPO_REPO = "projects/no1kmedi/personadiary-native-hypo-v1";

export function detectPersonadiaryRuntime(): PersonadiaryRuntimeSurface {
  if (typeof window === "undefined") return "unknown";
  const cap = (window as Window & { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor;
  if (cap?.isNativePlatform?.()) return "capacitor_webview";
  return "web_pwa";
}

export function getScreenTimeBridgeStatus(): ScreenTimeBridgeStatus {
  const runtime = detectPersonadiaryRuntime();
  if (runtime === "capacitor_webview") {
    return {
      status: "stub_pending_native",
      message_ko:
        "Capacitor WebView 감지 — Screen Time/UsageStats 플러그인은 아직 stub · 앱 차단·OS 제어 주장 금지",
      research_only: true,
    };
  }
  return {
    status: "unsupported_web",
    message_ko:
      "웹 PWA — iOS BGTask/Android WorkManager 미지원 · Pull-first UX만 · OS 제어 없음",
    research_only: true,
  };
}
