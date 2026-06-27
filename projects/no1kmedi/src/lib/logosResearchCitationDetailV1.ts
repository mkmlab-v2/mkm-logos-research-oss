import { formatPathStepHuman, stripStudioBoilerplate } from "@/lib/logosResearchStudioDisplayV1";
import {
  nodeIdsForRef,
  nodeLabelFromSlice,
  normalizeRefKey,
  type LogosGraphSliceNode,
} from "@/lib/logosResearchHighlightV1";
import type { VerseCitationShardEntry } from "@/lib/logosResearchVerseCitationShardV1";

export type CitationSelection =
  | { kind: "verse"; ref: string }
  | { kind: "node"; nodeId: string };

export type CitationDetailV1 = {
  title: string;
  subtitle: string;
  kindLabel: string;
  badges: string[];
  pathRole: string;
  pathNote: string | null;
  verseBodyKo: string | null;
  stageLabelKo: string | null;
  verseContextKo: string | null;
  pathSteps: string[];
  insightLine: string | null;
  answerExcerpt: string | null;
  governance: string | null;
  graphNodeIds: string[];
};

const KIND_LABEL_KO: Record<string, string> = {
  verse: "구절",
  theme: "테마",
  stage: "서사 단계",
  regime: "레짐",
  other: "맥락 노드",
};

type PathLike = {
  note_ko?: string | null;
  steps?: string[];
  verse_refs: string[];
  node_ids?: string[];
  reasoning_path_v1?: { node_ids?: string[]; path_label_ko?: string };
};

type ResultLike = {
  query?: string;
  answer?: string;
  path: PathLike;
  insight_card?: {
    gap_ko?: string;
    one_liner_ko?: string;
    governance?: string;
  } | null;
};

function kindLabel(kind?: string): string {
  return KIND_LABEL_KO[kind || "other"] || KIND_LABEL_KO.other;
}

function refInPathSteps(ref: string, steps: string[] = []): string | null {
  const key = normalizeRefKey(ref);
  for (const step of steps) {
    if (normalizeRefKey(step) === key) return step;
    if (step.includes(key)) return step;
  }
  return null;
}

function pathRoleForRef(
  ref: string,
  path: PathLike,
  graphNodeIds: string[],
): string {
  const spine = path.reasoning_path_v1?.node_ids || [];
  const onSpine = graphNodeIds.some((id) => spine.includes(id));
  const inVerseList = path.verse_refs.some((v) => normalizeRefKey(v) === normalizeRefKey(ref));
  const inSteps = refInPathSteps(ref, path.steps);

  if (onSpine && inVerseList) return "추론 spine · citation 경로에 포함";
  if (onSpine) return "추론 spine 노드";
  if (inVerseList && inSteps) return "경로 단계 · citation lock";
  if (inVerseList) return "경로 구절 목록 · 맥락 확장";
  if (inSteps) return "경로 단계에 연결";
  return "슬라이스 맥락 노드 · spine 외";
}

function versePathNote(
  ref: string,
  path: PathLike,
  matchedStep: string | null,
  shard?: VerseCitationShardEntry | null,
): string | null {
  if (matchedStep) {
    return `경로 spine · ${formatPathStepHuman(matchedStep)}`;
  }
  if (shard?.bottleneck_ko) {
    return shard.bottleneck_ko;
  }
  const stepHit = (path.steps || []).find(
    (s) => normalizeRefKey(s) === normalizeRefKey(ref) || s.includes(ref),
  );
  if (stepHit) {
    return `경로 단계 · ${formatPathStepHuman(stepHit)}`;
  }
  const isPrimary = path.verse_refs.some((v) => normalizeRefKey(v) === normalizeRefKey(ref));
  if (isPrimary && path.verse_refs[0] === ref && path.note_ko) {
    return stripStudioBoilerplate(path.note_ko);
  }
  return null;
}

function verseContextKo(shard?: VerseCitationShardEntry | null): string | null {
  if (!shard) return null;
  const parts: string[] = [];
  if (shard.stage_label_ko) parts.push(shard.stage_label_ko);
  if (shard.verse_note_ko && !shard.bottleneck_ko?.includes(shard.verse_note_ko.slice(0, 40))) {
    parts.push(shard.verse_note_ko);
  }
  return parts.length ? parts.join(" · ") : null;
}

function pathRoleForNode(nodeId: string, path: PathLike): string {
  const spine = path.reasoning_path_v1?.node_ids || [];
  const idx = spine.indexOf(nodeId);
  if (idx >= 0) {
    return idx === 0
      ? "추론 spine 시작"
      : idx === spine.length - 1
        ? "추론 spine 종착"
        : `추론 spine ${idx + 1}/${spine.length}`;
  }
  if (path.node_ids?.includes(nodeId)) return "동적 경로 highlight";
  return "망 탐색 · 로컬 mesh";
}

export function buildVerseCitationDetail(
  ref: string,
  result: ResultLike,
  nodeById: Record<string, LogosGraphSliceNode>,
  refToNodeIds: Record<string, string[]>,
  shardEntry?: VerseCitationShardEntry | null,
): CitationDetailV1 {
  const graphNodeIds = nodeIdsForRef(ref, refToNodeIds);
  const primary = graphNodeIds[0] ? nodeById[graphNodeIds[0]] : undefined;
  const matchedStep = refInPathSteps(ref, result.path.steps);
  const pathSteps = (result.path.steps || [])
    .slice(0, 6)
    .map((s) => formatPathStepHuman(s));

  return {
    title: ref,
    subtitle: shardEntry?.stage_label_ko
      ? shardEntry.stage_label_ko
      : primary?.label && primary.label !== ref
        ? primary.label
        : "",
    kindLabel: kindLabel(primary?.kind || "verse"),
    badges: [
      kindLabel(primary?.kind || "verse"),
      pathRoleForRef(ref, result.path, graphNodeIds),
    ],
    pathRole: pathRoleForRef(ref, result.path, graphNodeIds),
    pathNote: versePathNote(ref, result.path, matchedStep, shardEntry),
    verseBodyKo: shardEntry?.text_ko || null,
    stageLabelKo: shardEntry?.stage_label_ko || null,
    verseContextKo: verseContextKo(shardEntry),
    pathSteps: matchedStep
      ? [formatPathStepHuman(matchedStep), ...pathSteps.filter((s) => s !== formatPathStepHuman(matchedStep!))].slice(0, 4)
      : pathSteps,
    insightLine: result.insight_card?.one_liner_ko
      ? stripStudioBoilerplate(result.insight_card.one_liner_ko)
      : result.path.reasoning_path_v1?.path_label_ko || null,
    answerExcerpt: result.answer ? stripStudioBoilerplate(result.answer).slice(0, 280) : null,
    governance: shardEntry?.governance || result.insight_card?.governance || "[HYPO][NON_GATING]",
    graphNodeIds,
  };
}

export function buildNodeCitationDetail(
  nodeId: string,
  result: ResultLike,
  nodeById: Record<string, LogosGraphSliceNode>,
): CitationDetailV1 {
  const node = nodeById[nodeId];
  const label = nodeLabelFromSlice(nodeId, nodeById);
  const ref = node?.ref || (label.includes(".") ? label : "");
  const pathSteps = (result.path.steps || [])
    .slice(0, 6)
    .map((s) => formatPathStepHuman(s));

  let stageHint: string | null = null;
  if (node?.kind === "stage") {
    stageHint = `${label} — 욥기 서사 구간 앵커`;
  } else if (node?.kind === "theme") {
    stageHint = `테마 브릿지 · ${label}`;
  }

  return {
    title: label,
    subtitle: ref && ref !== label ? ref : nodeId.split("::").slice(-2).join(" · "),
    kindLabel: kindLabel(node?.kind),
    badges: [kindLabel(node?.kind), pathRoleForNode(nodeId, result.path)],
    pathRole: pathRoleForNode(nodeId, result.path),
    pathNote: stageHint || (result.path.note_ko ? stripStudioBoilerplate(result.path.note_ko) : null),
    verseBodyKo: null,
    stageLabelKo: node?.kind === "stage" ? label : null,
    verseContextKo: null,
    pathSteps,
    insightLine:
      result.path.reasoning_path_v1?.path_label_ko ||
      result.insight_card?.one_liner_ko ||
      null,
    answerExcerpt: null,
    governance: result.insight_card?.governance || "[HYPO][NON_GATING]",
    graphNodeIds: [nodeId],
  };
}

export function buildCitationDetail(
  selection: CitationSelection,
  result: ResultLike,
  nodeById: Record<string, LogosGraphSliceNode>,
  refToNodeIds: Record<string, string[]>,
  shardEntry?: VerseCitationShardEntry | null,
): CitationDetailV1 {
  if (selection.kind === "verse") {
    return buildVerseCitationDetail(selection.ref, result, nodeById, refToNodeIds, shardEntry);
  }
  return buildNodeCitationDetail(selection.nodeId, result, nodeById);
}
