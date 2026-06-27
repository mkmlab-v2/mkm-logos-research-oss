"use client";

import type { ReactNode } from "react";

import { ClinicianConsultGraphPanel } from "@/components/ClinicianConsultGraphPanel";
import { ClinicianGraphConflictSheet } from "@/components/ClinicianGraphConflictSheet";
import { ClinicianCanvasCitationLockPanel } from "@/components/clinician/ClinicianCanvasCitationLockPanel";
import {
  buildClinicianCanvasScope,
  buildThinkingStepsFromCdsReasoning,
} from "@/lib/clinicianCanvasAdapterV1";
import {
  MkmPathThinkingTimeline,
} from "@/components/trust-canvas/MkmPathThinkingTimeline";
import { MkmTrustCanvasShell } from "@/components/trust-canvas/MkmTrustCanvasShell";

type Props = {
  chat: ReactNode;
  loading?: boolean;
  requestId: string;
  envelope: Record<string, unknown>;
  reasoning?: {
    syndrome_hypothesis?: string;
    care_direction?: string;
    caution?: string;
  };
  clinicalSummary?: string;
  validationOk?: boolean;
  patientCareBundle?: Record<string, unknown> | null;
  headerActions?: ReactNode;
};

export function ClinicianCanvasStudioLayout({
  chat,
  loading = false,
  requestId,
  envelope,
  reasoning,
  clinicalSummary,
  validationOk,
  patientCareBundle,
  headerActions,
}: Props) {
  const thinkingSteps = buildThinkingStepsFromCdsReasoning(reasoning);

  const canvasBody = (
    <ClinicianConsultGraphPanel
      requestId={requestId}
      envelope={envelope}
      reasoning={reasoning}
      patientCareBundle={patientCareBundle}
    />
  );

  const evidence = (
    <div className="clinician-canvas-evidence-wrapper">
      {clinicalSummary ? (
        <div className="clinician-canvas-evidence-summary">
          <h4>임상 요약</h4>
          <p>{clinicalSummary}</p>
        </div>
      ) : null}
      <ClinicianGraphConflictSheet
        requestId={requestId}
        envelope={envelope}
        reasoning={reasoning}
        patientCareBundle={patientCareBundle}
      />
    </div>
  );

  return (
    <div className="clinician-canvas-page clinician-canvas-theme" data-clinician-canvas-studio="1">
      <MkmTrustCanvasShell
        domainId="clinician"
        scope={buildClinicianCanvasScope(validationOk)}
        headerActions={headerActions}
        chat={chat}
        thinking={
          <MkmPathThinkingTimeline
            steps={thinkingSteps}
            loading={loading}
            title="CDS 조립"
            emptyHint="CDS 초안 생성 후 증후·케어·주의 단계가 표시됩니다."
          />
        }
        canvas={canvasBody}
        citationDock={
          <ClinicianCanvasCitationLockPanel
            requestId={requestId}
            validationOk={validationOk}
            syndromeHypothesis={reasoning?.syndrome_hypothesis}
            caution={reasoning?.caution}
          />
        }
        evidence={evidence}
      />
    </div>
  );
}
