import { PersonadiaryChrome } from "@/components/PersonadiaryChrome";
import { PersonadiaryOpsHome } from "@/components/personadiary/PersonadiaryOpsHome";

export const dynamic = "force-dynamic";

export default function PersonadiaryOpsPage() {
  return (
    <PersonadiaryChrome premium ops>
      <main id="main" className="pd-main-ops pd-main-ops--ios">
        <p className="pd-ops-export-marker" hidden>
          pd-ops-export · pd-ops-import · pd-ops-native-hypo · pd-ops-voice-hypo · B-track manual export · Human Gate
        </p>
        <p className="pd-non-prediction-contract" hidden data-contract="non_prediction_v1">
          pd-non-prediction-contract · 정신적 방화벽 · SEND_GATE: HOLD · 예언·적중·%·운세 단정 없음
        </p>
        <p className="pd-pwa-install" hidden>
          pd-pwa-install · iOS A2HS · Android beforeinstallprompt
        </p>
        <PersonadiaryOpsHome />
      </main>
    </PersonadiaryChrome>
  );
}
