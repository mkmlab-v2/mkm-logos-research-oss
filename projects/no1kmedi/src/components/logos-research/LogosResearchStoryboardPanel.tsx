"use client";

import Link from "next/link";

import { LogosScriptoriumReportPanel } from "@/components/logos-research/LogosScriptoriumReportPanel";
import { stripStudioBoilerplate, formatPathStepHuman, verseRefShortList } from "@/lib/logosResearchStudioDisplayV1";
import {
  ECS_LOW_REQUERY_POC_HINT_KO,
  buildEcsExpandPocStudioUrl,
  ecsV1Tooltip,
  shouldSuggestEcsRequeryPoc,
} from "@/lib/logosStudioEcsLowRequeryPocV1";
import type { LogosStoryboardSlotId } from "@/lib/logosStudioHeroDemoBeatsV1";
import type { GraphSliceCoverage } from "@/lib/logosStudioGraphCoverageV1";
import type { ConflictContextResult } from "@/lib/logosStudioConflictBridgeV1";

export type StoryboardResult = {
  query: string;
  answer: string;
  query_mode?: string;
  path: {
    note_ko?: string | null;
    steps?: string[];
    verse_refs: string[];
    bridges_matched?: number | null;
  };
  synthesis_meta?: {
    synthesis_mode?: string;
    llm_invoked?: boolean;
  } | null;
  conflict_context?: Extract<ConflictContextResult, { ok: true }> | null;
  graphrag_meta?: {
    bridges_matched?: number;
    paths_count?: number;
  };
  insight_card?: {
    gap_ko?: string;
    one_liner_ko?: string;
    governance?: string;
  } | null;
  evidence_confidence?: {
    ecs_v1?: number;
    band?: "low" | "mid" | "high";
    components?: {
      path_depth_ratio?: number;
      cited_refs_strength?: number;
      conflict_entropy_penalty?: number;
    };
    note_ko?: string;
  } | null;
};

type Props = {
  result: StoryboardResult;
  coverage: GraphSliceCoverage;
  onVerseRefClick?: (ref: string) => void;
  showAuditorHint?: boolean;
  activeSlot?: LogosStoryboardSlotId | null;
  presetId?: string;
  /** Antigravity scriptorium: markdown-style report, hide dev meta */
  variant?: "default" | "scriptorium";
  bloomSecondaryHintKo?: string;
};

function slotClass(slot: LogosStoryboardSlotId, activeSlot: LogosStoryboardSlotId | null | undefined): string {
  const base = `lr-studio-story-slot lr-studio-story-slot--${slot}`;
  return activeSlot === slot ? `${base} lr-studio-story-slot--active` : base;
}

function modeLabel(mode: string | undefined): string {
  if (!mode) return "프리셋 경로";
  if (mode.includes("synthesis")) return "학파 병렬 합성";
  if (mode.includes("graphrag")) return "동적 GraphRAG";
  return mode;
}

function schoolParallelMeta(
  conflict: StoryboardResult["conflict_context"],
  synthesisMode: string | undefined,
): { active: boolean; schoolCount: number; labelKo: string } {
  const groups = conflict?.ok ? conflict.groups : [];
  let schoolCount = 0;
  for (const g of groups) {
    const n = g.school_count ?? g.schools?.length ?? 0;
    schoolCount += n;
  }
  const synthParallel = String(synthesisMode || "").includes("parallel");
  const active = synthParallel || schoolCount >= 2 || groups.length >= 2;
  const labelKo = active
    ? `학파 병렬 ${Math.max(schoolCount, groups.length)} · AB rubric school_parallel`
    : "학파 병렬 미확인 — BigSet·합성 질의에서만";
  return { active, schoolCount, labelKo };
}

export function LogosResearchStoryboardPanel({
  result,
  coverage,
  onVerseRefClick,
  showAuditorHint = false,
  activeSlot = null,
  presetId,
  variant = "default",
  bloomSecondaryHintKo,
}: Props) {
  const scriptorium = variant === "scriptorium";
  const lead = result.synthesis_meta?.synthesis_mode
    ? stripStudioBoilerplate(result.answer)
    : stripStudioBoilerplate(result.path.note_ko || result.answer || "");

  const bridges =
    result.graphrag_meta?.bridges_matched ?? result.path.bridges_matched ?? null;
  const pathsCount = result.graphrag_meta?.paths_count ?? null;
  const conflict = result.conflict_context;
  const steps = result.path.steps ?? [];
  const ecs = result.evidence_confidence;
  const hasEcs = typeof ecs?.ecs_v1 === "number";
  const gapKo = result.insight_card?.gap_ko?.trim() || "";
  const schoolParallel = schoolParallelMeta(conflict, result.synthesis_meta?.synthesis_mode);
  const showEcsRequeryPoc = shouldSuggestEcsRequeryPoc(ecs?.band) && presetId;

  return (
    <div
      className={`lr-studio-storyboard${scriptorium ? " lr-studio-storyboard--scriptorium" : ""}`}
      aria-labelledby="lr-studio-storyboard-title"
    >
      <header className="lr-studio-storyboard-head">
        <h3 id="lr-studio-storyboard-title">
          {scriptorium ? "구조화 분석" : "통찰 스토리보드"}
        </h3>
        {!scriptorium ? (
          <>
            <p className="lr-studio-storyboard-meta">
              Field → Lens → Conflict → Gap → 한 줄 · [HYPO] research_only
            </p>
            {coverage.totalVerseRefs > 0 ? (
              <p className="lr-studio-storyboard-coverage" role="status">
                그래프 슬라이스 매핑 {coverage.mappedVerseRefs}/{coverage.totalVerseRefs} 구절
                {coverage.unmappedRefs.length
                  ? ` · 미포함 ${coverage.unmappedRefs.slice(0, 4).join(", ")}${coverage.unmappedRefs.length > 4 ? "…" : ""}`
                  : ""
                }
              </p>
            ) : null}
          </>
        ) : bloomSecondaryHintKo ? (
          <p
            className="lr-studio-storyboard-bloom-hint"
            data-logos-bloom-secondary="1"
            role="status"
          >
            {bloomSecondaryHintKo}
          </p>
        ) : null}
      </header>

      {scriptorium ? (
        <LogosScriptoriumReportPanel result={result} />
      ) : (
      <ol className="lr-studio-storyboard-rail">
        <li className={slotClass("field", activeSlot)}>
          <span className="lr-studio-story-slot-label">Field</span>
          <p className="lr-studio-story-slot-query">{result.query}</p>
          {result.path.note_ko ? (
            <p className="lr-studio-story-slot-body">{stripStudioBoilerplate(result.path.note_ko)}</p>
          ) : null}
          {result.path.verse_refs.length ? (
            <div className="lr-studio-story-verse-row" aria-label="구절 앵커">
              {verseRefShortList(result.path.verse_refs, 10).map((ref) =>
                onVerseRefClick ? (
                  <button
                    key={ref}
                    type="button"
                    className="lr-studio-verse-pill lr-studio-verse-pill--btn"
                    onClick={() => onVerseRefClick(ref)}
                    title="감사 보기에서 구절 포커스"
                  >
                    {ref}
                  </button>
                ) : (
                  <span key={ref} className="lr-studio-verse-pill">
                    {ref}
                  </span>
                ),
              )}
            </div>
          ) : null}
          {showAuditorHint && onVerseRefClick ? (
            <p className="lr-studio-story-slot-muted">구절 칩 클릭 → 경로 마인드맵에서 citation pulse</p>
          ) : null}
        </li>

        <li className={slotClass("lens", activeSlot)}>
          <span className="lr-studio-story-slot-label">
            Lens <span className="lr-studio-story-non-gating">[NON_GATING]</span>
          </span>
          <p className="lr-studio-story-slot-body">
            {modeLabel(result.query_mode)}
            {bridges != null ? ` · bridge ${bridges}` : ""}
            {pathsCount != null ? ` · paths ${pathsCount}` : ""}
          </p>
          {hasEcs ? (
            <details className="lr-studio-story-ecs-details">
              <summary title={ecsV1Tooltip(ecs?.note_ko)}>
                <span
                  className={`lr-studio-story-ecs-badge lr-studio-story-ecs-badge--${ecs?.band ?? "mid"}`}
                  title={ecsV1Tooltip(ecs?.note_ko)}
                >
                  ECS {ecs?.ecs_v1}
                </span>
                <span className="lr-studio-story-ecs-hint">근거 가시성 계산 보기</span>
              </summary>
              <p className="lr-studio-story-slot-muted">
                path {Math.round((ecs?.components?.path_depth_ratio ?? 0) * 100)} · refs{" "}
                {Math.round((ecs?.components?.cited_refs_strength ?? 0) * 100)} · penalty{" "}
                {Math.round((ecs?.components?.conflict_entropy_penalty ?? 0) * 100)}
              </p>
              {ecs?.note_ko ? <p className="lr-studio-story-slot-muted">{ecs.note_ko}</p> : null}
            </details>
          ) : null}
          {showEcsRequeryPoc ? (
            <p className="lr-studio-story-ecs-requery-poc" role="note">
              {ECS_LOW_REQUERY_POC_HINT_KO}{" "}
              <Link href={buildEcsExpandPocStudioUrl(presetId!)} className="lr-studio-story-ecs-requery-link">
                확장 재조회 PoC →
              </Link>
            </p>
          ) : null}
          {steps.length ? (
            <ol className="lr-studio-story-steps">
              {steps.slice(0, 8).map((step) => (
                <li key={step}>{formatPathStepHuman(step)}</li>
              ))}
            </ol>
          ) : (
            <p className="lr-studio-story-slot-muted">경로 단계 없음 — 프리셋 앵커만</p>
          )}
        </li>

        <li className={slotClass("conflict", activeSlot)}>
          <span className="lr-studio-story-slot-label">Conflict</span>
          {conflict?.ok && conflict.group_count > 0 ? (
            <>
              <p className="lr-studio-story-slot-body">
                BigSet 학파 격벽 {conflict.group_count}그룹
                {conflict.groups[0]?.lexicon_base
                  ? ` · ${conflict.groups[0].lexicon_base}`
                  : ""}
              </p>
              <p
                className={`lr-studio-story-school-parallel${schoolParallel.active ? " lr-studio-story-school-parallel--on" : ""}`}
                role="status"
              >
                {schoolParallel.labelKo}
              </p>
              <p className="lr-studio-story-slot-muted">
                {conflict.ui_contract?.disclaimer_ko ??
                  "단일 학파 우위 없음 · citation lock 전 연구용"}
              </p>
            </>
          ) : (
            <p className="lr-studio-story-slot-muted">
              이 질의에는 BigSet 학파 격벽 미부착 — 왼쪽 패널 또는 BigSet 토픽 질의 시 표시
            </p>
          )}
        </li>

        <li className={slotClass("gap", activeSlot)}>
          <span className="lr-studio-story-slot-label">Gap</span>
          {gapKo ? (
            <p className="lr-studio-story-gap-body" role="status">
              {gapKo}
            </p>
          ) : (
            <p className="lr-studio-story-slot-muted">
              구조적 갭 미기재 — 전량 TSK·open LLM 아님 · why 단답 조립 없음
            </p>
          )}
          <p className="lr-studio-story-slot-muted">
            답변 전에 한계를 먼저 확인하세요 · [HYPO] NON_GATING
          </p>
        </li>

        <li className={slotClass("final", activeSlot)}>
          <span className="lr-studio-story-slot-label">한 줄</span>
          {lead ? (
            <blockquote className="lr-studio-story-final">{lead}</blockquote>
          ) : (
            <p className="lr-studio-story-slot-muted">합성·경로 요약 대기</p>
          )}
          {result.synthesis_meta?.synthesis_mode ? (
            <p className="lr-studio-story-synth-tag" role="status">
              {result.synthesis_meta.synthesis_mode}
              {result.synthesis_meta.llm_invoked ? " · LLM" : " · 결정론"}
            </p>
          ) : null}
        </li>
      </ol>
      )}
    </div>
  );
}
