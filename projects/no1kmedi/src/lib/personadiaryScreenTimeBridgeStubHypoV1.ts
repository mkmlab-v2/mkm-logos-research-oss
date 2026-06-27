/**
 * Screen Time / UsageStats bridge stub — [HYPO] research_only.
 * SSOT: docs/final/artifacts/personadiary_focus_shield_hypo_v1_latest.json
 */
import { detectPersonadiaryRuntime } from "./personadiaryNativeBridgeHypoV1";

export const PERSONADIARY_FOCUS_SHIELD_BRIDGE_SCHEMA = "personadiary_focus_shield_bridge_hypo_v1" as const;

export type ScreenTimeStubCapability =
  | "unsupported_web"
  | "native_webview_no_plugin"
  | "plugin_stub_registered";

export type ScreenTimeStubProbe = {
  capability: ScreenTimeStubCapability;
  research_only: true;
  hypothesis_tier: "B";
  can_request_permissions: false;
  can_block_apps: false;
  message_ko: string;
};

export type FocusShieldBridgeProbeV1 = ScreenTimeStubProbe & {
  schema: typeof PERSONADIARY_FOCUS_SHIELD_BRIDGE_SCHEMA;
};

export function toFocusShieldBridgeProbe(stub: ScreenTimeStubProbe): FocusShieldBridgeProbeV1 {
  return { schema: PERSONADIARY_FOCUS_SHIELD_BRIDGE_SCHEMA, ...stub };
}

export function probeScreenTimeBridgeStub(): ScreenTimeStubProbe {
  const runtime = detectPersonadiaryRuntime();
  if (runtime === "web_pwa") {
    return {
      capability: "unsupported_web",
      research_only: true,
      hypothesis_tier: "B",
      can_request_permissions: false,
      can_block_apps: false,
      message_ko: "웹 PWA — Screen Time API 미연결 (stub)",
    };
  }
  return {
    capability: "native_webview_no_plugin",
    research_only: true,
    hypothesis_tier: "B",
    can_request_permissions: false,
    can_block_apps: false,
    message_ko:
      "Capacitor WebView — 커스텀 Screen Time 플러그인 PoC 전 · 앱 차단 불가 · OS 제어 주장 금지",
  };
}
