"use client";

import { useEffect, useState, type ReactNode } from "react";

import { LogosResearchCitationSidecarPanel } from "@/components/logos-research/LogosResearchCitationSidecarPanel";
import { LogosResearchConflictSidecarPanel } from "@/components/logos-research/LogosResearchConflictSidecarPanel";
import { LogosResearchInsightLatticePanel } from "@/components/logos-research/LogosResearchInsightLatticePanel";
import {
  LogosResearchSubgraphPanel,
  type LogosSubgraphCitationSlotPayload,
} from "@/components/logos-research/LogosResearchSubgraphPanel";
import {
  MkmPathThinkingTimeline,
} from "@/components/trust-canvas/MkmPathThinkingTimeline";
import { MkmTrustCanvasShell } from "@/components/trust-canvas/MkmTrustCanvasShell";
import { logosResearchCopy } from "@/content/logosResearchCopy";
import { buildScriptoriumThinkingSteps } from "@/lib/logosResearchStudioDisplayV1";
import type { ConflictContextResult } from "@/lib/logosStudioConflictBridgeV1";
import type { LogosStudioAudienceMode } from "@/lib/logosStudioAudienceModeV1";

import type { StudioSubgraphResult } from "@/components/logos-research/LogosResearchSubgraphPanel";

type Props = {
  chat: ReactNode;
  loading: boolean;
  result: StudioSubgraphResult | null;
  conflictContext?: Extract<ConflictContextResult, { ok: true }> | null;
  autorun: boolean;
  activePresetId: string;
  onGapChipClick: (chip: { bridge_question_ko?: string; label_ko?: string }) => void;
  gapFocusLabel: string | null;
  headerActions?: ReactNode;
  audienceMode?: LogosStudioAudienceMode;
};

export function LogosCanvasStudioLayout({
  chat,
  loading,
  result,
  conflictContext,
  autorun,
  activePresetId,
  onGapChipClick,
  gapFocusLabel,
  headerActions,
  audienceMode = "academic",
}: Props) {
  const [citationSlot, setCitationSlot] = useState<LogosSubgraphCitationSlotPayload | null>(null);

  useEffect(() => {
    if (!result) setCitationSlot(null);
  }, [result]);

  const thinkingSteps = buildScriptoriumThinkingSteps();

  const canvasBody = result ? (
    <LogosResearchSubgraphPanel
      result={result}
      autoDemoOnMount={autorun}
      productDemoMode={false}
      citationPlacement="external"
      scriptoriumMode
      onCitationSlotChange={setCitationSlot}
    />
  ) : loading ? (
    <div className="mkm-trust-canvas-placeholder" aria-busy="true">
      <p className="mkm-trust-canvas-placeholder-title">경로 엔진 실행 중…</p>
      <div className="lr-studio-graph-skeleton" aria-hidden="true" />
    </div>
  ) : (
    <div className="mkm-trust-canvas-placeholder">
      <p className="mkm-trust-canvas-placeholder-title">경로 캔버스</p>
      <p className="mkm-trust-canvas-placeholder-body">
        질문을 실행하면 스토리보드·마인드맵·구절 인용이 이 영역에 표시됩니다.
      </p>
    </div>
  );

  const evidencePanel = result ? (
      <>
        {conflictContext?.ok && conflictContext.group_count > 0 ? (
          <LogosResearchConflictSidecarPanel context={conflictContext} />
        ) : null}
        <LogosResearchInsightLatticePanel
          activePresetId={activePresetId}
          onGapChipClick={onGapChipClick}
        />
        {gapFocusLabel ? (
          <p className="lr-studio-gap-focus" role="status">
            {gapFocusLabel}
          </p>
        ) : null}
      </>
    ) : null;

  const audienceCopy =
    "audience_modes" in (logosResearchCopy.studio || {})
      ? (logosResearchCopy.studio as { audience_modes?: Record<string, string> }).audience_modes
      : undefined;

  const scope =
    audienceMode === "pastoral"
      ? {
          label: audienceCopy?.scope_label_pastoral ?? "Logos Canvas · 묵상·고민",
          detail:
            audienceCopy?.scope_detail_pastoral ??
            "320-node slice · citation lock · 관측 전용 [NON_GATING]",
          tags: ["research_only", "not_counseling", "send_gate HOLD"],
        }
      : {
          label: "Logos Canvas · curated graph slice",
          detail: "320-node slice · citation lock · ECS [NON_GATING]",
          tags: ["research_only", "send_gate HOLD"],
        };

  return (
    <MkmTrustCanvasShell
      domainId="logos"
      className="mkm-trust-canvas--scriptorium"
      scope={scope}
      headerActions={headerActions}
      chat={chat}
      thinking={
        <MkmPathThinkingTimeline
          steps={thinkingSteps}
          loading={loading}
          title="생각 단계"
          variant="scriptorium"
        />
      }
      canvas={canvasBody}
      citationDock={
        citationSlot ? (
          <LogosResearchCitationSidecarPanel
            detail={citationSlot.detail}
            onOpenExplore={citationSlot.onOpenExplore}
            onClear={citationSlot.onClear}
            variant="scriptorium"
          />
        ) : null
      }
      evidence={
        result ? (
          <details className="lr-scriptorium-evidence-drawer">
            <summary>고급 · 격벽 · lattice</summary>
            {evidencePanel}
          </details>
        ) : null
      }
    />
  );
}
