import { PersonadiaryChrome } from "@/components/PersonadiaryChrome";
import { PersonadiaryOpsEdgeBridge } from "@/components/personadiary/PersonadiaryOpsEdgeBridge";
import { PersonadiaryOpsHome } from "@/components/personadiary/PersonadiaryOpsHome";

export const dynamic = "force-dynamic";

export default function PersonadiaryOpsPage() {
  return (
    <PersonadiaryChrome premium ops>
      <PersonadiaryOpsEdgeBridge />
      <main
        id="main"
        className="pd-main-ops pd-main-ops--ios pd-main-ops--commercial pd-main-ops--fab"
      >
        <p className="pd-ops-export-marker" hidden>
          pd-ops-commercial-v1 · pd-ops-export · pd-ops-import · pd-ops-native-hypo · pd-ops-native-intent-hypo · pd-ops-voice-hypo · pd-ops-fab-v1 · pd-android-edge-insets-v1 · pd-logos-sidebar-hypo-v1 · B-track manual export · Human Gate
        </p>
        <p className="pd-non-prediction-contract" hidden data-contract="non_prediction_v1">
          pd-non-prediction-contract · 정신적 방화벽 · SEND_GATE: HOLD · 예언·적중·%·운세 단정 없음
        </p>
        <p className="pd-ops-trust-wedge" hidden data-trust-wedge="trust_composition_v1">
          artifact·게이트 없이 예측·적중·운세 단정을 하지 않습니다.
        </p>
        <p className="pd-pwa-install" hidden>
          pd-pwa-install · iOS A2HS · Android beforeinstallprompt
        </p>
        <p className="pd-logos-sidebar-hypo-v1" hidden data-contract="logos_sidebar_non_gating_v1">
          pd-logos-sidebar-hypo-v1 · Logos 참조 지도 · NON_GATING · opt-in sidebar
        </p>
        <p className="pd-ops-native-intent-hypo-v1" hidden data-contract="native_intent_middleware_v1">
          Intent 미들웨어 · pd-ops-native-intent-hypo · preview_only · Pull-first 큐
        </p>
        <p className="pd-android-edge-to-edge-v1" hidden data-contract="android_edge_to_edge_p0_v1">
          pd-android-edge-to-edge-v1 · Capacitor WebView edge-to-edge · --pd-safe-* CSS · native WindowCompat
        </p>
        <p className="pd-ops-cache-hint" hidden>
          pd-ops-cache-hint · 강력 새로고침 Ctrl+Shift+R
        </p>
        <PersonadiaryOpsHome />
      </main>
    </PersonadiaryChrome>
  );
}
