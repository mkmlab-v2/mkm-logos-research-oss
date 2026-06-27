"use client";

import { ClinicianCanvasCitationLockPanel } from "@/components/clinician/ClinicianCanvasCitationLockPanel";
import { buildClinicianCanvasScope } from "@/lib/clinicianCanvasAdapterV1";
import { MkmPathThinkingTimeline } from "@/components/trust-canvas/MkmPathThinkingTimeline";
import { MkmTrustCanvasShell } from "@/components/trust-canvas/MkmTrustCanvasShell";

type Props = {
  onOpenChat: () => void;
};

export function ClinicianCanvasEmptyLayout({ onOpenChat }: Props) {
  const canvasBody = (
    <div className="mkm-trust-canvas-placeholder" data-clinician-canvas-placeholder-canvas="1">
      <p className="mkm-trust-canvas-placeholder-title">CDS 그래프 캔버스</p>
      <p className="mkm-trust-canvas-placeholder-body">
        진료 보조(CDS) 초안이 준비되면 증후·케어 경로 그래프와 갈등 시트가 이 영역에 표시됩니다.
      </p>
      <div className="clinician-canvas-placeholder-skeleton" aria-hidden="true" />
    </div>
  );

  return (
    <div
      className="clinician-canvas-page clinician-canvas-theme clinician-canvas-page--empty"
      data-clinician-canvas-studio="1"
      data-clinician-canvas-empty="1"
      data-clinician-canvas-placeholder="1"
    >
      <MkmTrustCanvasShell
        domainId="clinician"
        scope={buildClinicianCanvasScope(false)}
        chat={
          <>
            <h2 className="workspace-panel-title">Encounter</h2>
            <p className="workspace-muted">
              Trust Canvas · CDS 봉투 대기 중.{" "}
              <button type="button" className="workspace-link-btn" onClick={onOpenChat}>
                대화 탭
              </button>
              에서 진료 보조를 실행하세요.
            </p>
          </>
        }
        thinking={
          <MkmPathThinkingTimeline
            steps={[]}
            title="CDS 조립"
            emptyHint="CDS 초안 생성 후 증후·케어·주의 단계가 표시됩니다."
          />
        }
        canvas={canvasBody}
        citationDock={
          <ClinicianCanvasCitationLockPanel
            requestId="pending"
            validationOk={false}
          />
        }
        evidence={
          <p className="clinician-canvas-evidence-empty workspace-muted">
            [NON_GATING] 보조 초안 · 한의사 최종 확정 전 · send_gate HOLD
          </p>
        }
      />
    </div>
  );
}
