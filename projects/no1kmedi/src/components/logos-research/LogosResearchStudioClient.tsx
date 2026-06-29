"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { LogosCanvasStudioLayout } from "@/components/logos-research/LogosCanvasStudioLayout";
import { LogosStudioOmniEntry } from "@/components/logos-research/LogosStudioOmniEntry";
import { LogosStudioOnboardingOverlay } from "@/components/logos-research/LogosStudioOnboardingOverlay";
import {
  dispatchScriptoriumVerseSelect,
  LogosStudioScriptoriumInquiry,
} from "@/components/logos-research/LogosStudioScriptoriumInquiry";
import { LogosResearchConflictSidecarPanel } from "@/components/logos-research/LogosResearchConflictSidecarPanel";
import { LogosResearchInsightLatticePanel } from "@/components/logos-research/LogosResearchInsightLatticePanel";
import {
  LogosResearchSasangNetworkKpiStrip,
  LogosResearchSasangNetworkSummaryPanel,
} from "@/components/logos-research/LogosResearchSasangNetworkSummaryPanel";
import { LogosResearchSubgraphPanel } from "@/components/logos-research/LogosResearchSubgraphPanel";
import Link from "next/link";

import { logosResearchCopy } from "@/content/logosResearchCopy";
import { ecsV1Tooltip } from "@/lib/logosStudioEcsLowRequeryPocV1";
import {
  defaultPresetIdForAudienceMode,
  filterPresetsByAudienceMode,
  LOGOS_PASTORAL_SLOT_LABEL_KO,
  LOGOS_STUDIO_AUDIENCE_MODES,
  parseLogosStudioAudienceMode,
  type LogosStudioAudienceMode,
} from "@/lib/logosStudioAudienceModeV1";
import { isEmbedDemoPreset, LOGOS_FREE_DAILY_QUOTA } from "@/lib/logosResearchQuotaV1";
import type { ConflictContextResult } from "@/lib/logosStudioConflictBridgeV1";
import { buildScriptoriumTopicPills, buildScriptoriumInquirySummary, verseRefShortList } from "@/lib/logosResearchStudioDisplayV1";
import {
  LOGOS_STUDIO_OMNI_QUICK_PRESET_IDS,
  resolveInitialStudioPhase,
  type LogosStudioPhase,
} from "@/lib/logosStudioPhaseV1";
import {
  markLogosStudioOnboardingComplete,
  shouldShowLogosStudioOnboarding,
  type LogosStudioOnboardingResult,
} from "@/lib/logosStudioOnboardingV1";
import {
  createLogosQueryPipeline,
  patchLogosQueryPipeline,
  resetLogosQueryPipeline,
} from "@/lib/logos-studio-pipeline-v1";

type PresetRow = { id: string; prompt_ko: string; slot?: string | null; slot_label_ko?: string | null };

type InsightCard = {
  slot?: string;
  slot_label_ko?: string;
  one_liner_ko?: string;
  verse_anchors?: string[];
  gap_ko?: string;
};

type QueryResult = {
  preset_id: string;
  query: string;
  answer: string;
  insight_card?: InsightCard | null;
  query_mode?: string;
  path: {
    note_ko: string | null;
    steps: string[];
    verse_refs: string[];
    node_ids?: string[];
    bridges_matched: number | null;
    reasoning_path_v1?: { node_ids?: string[]; path_label_ko?: string };
  };
  highlight_node_ids: string[];
  subgraph?: { graph_slice_url: string; highlight_count: number };
  graphrag_meta?: {
    bridges_matched?: number;
    paths_count?: number;
    skipped?: boolean;
    paths_preview?: Array<{ path_id?: string; note_ko?: string }>;
  };
  synthesis_meta?: {
    synthesis_mode?: string;
    llm_invoked?: boolean;
    citation_valid?: boolean;
  } | null;
  evidence_confidence?: {
    ecs_v1?: number;
    band?: "low" | "mid" | "high";
    note_ko?: string;
  } | null;
  conflict_context?: Extract<ConflictContextResult, { ok: true }> | null;
};

type LeadState = "idle" | "submitting" | "ok" | "error";

const STUDIO_FETCH_TIMEOUT_MS = 15000;
const STUDIO_LOADING_TIMEOUT_MS = 18000;

async function postStudioTelemetry(payload: Record<string, unknown>) {
  try {
    await fetch("/api/telemetry/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    });
  } catch {
    // best effort telemetry only
  }
}

async function fetchStudioJson(
  url: string,
  init?: RequestInit,
  timeoutMs = STUDIO_FETCH_TIMEOUT_MS,
): Promise<Record<string, unknown>> {
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...init, signal: ctrl.signal, cache: "no-store" });
    const text = await res.text();
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(text) as Record<string, unknown>;
    } catch {
      throw new Error(`invalid_json_http_${res.status}`);
    }
    if (!res.ok) {
      const apiErr = typeof data.error === "string" ? data.error : `http_${res.status}`;
      throw new Error(apiErr);
    }
    return data;
  } catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") throw new Error("fetch_timeout");
    throw e;
  } finally {
    window.clearTimeout(timer);
  }
}

function graphragModeLabel(mode: string | undefined): string {
  if (!mode) return "";
  if (mode.includes("synthesis")) return "학파 병렬 합성";
  if (mode === "graphrag_only") return "동적 경로";
  if (mode === "preset+graphrag_custom") return "질문 맞춤 경로";
  if (mode === "preset+graphrag") return "프리셋 + 동적 보강";
  if (mode === "preset") return "프리셋 번들";
  return mode;
}

function buildStudioDemoUrl(presetId: string, queryText: string): string {
  const params = new URLSearchParams();
  params.set("demo", "1");
  params.set("autorun", "1");
  if (presetId) params.set("q", presetId);
  else if (queryText.trim()) params.set("q", queryText.trim());
  return `/logos-research/studio?${params.toString()}`;
}

function presetMatchLabel(match: string | undefined): string {
  if (!match || match === "none") return "";
  if (match.startsWith("query_guard_")) return "질의 spine 자동 전환";
  if (match === "embedding") return "의미 라우터 (tier-2)";
  if (match === "lexical") return "키워드 매칭";
  if (match === "text") return "질문 일치";
  if (match === "id") return "프리셋 직접";
  return match;
}

function resolveInitialPresetSelection(
  rows: PresetRow[],
  opts: { presetFromUrl: string; hubPrefill: string; defaultPreset: string },
): { presetId: string; query: string } {
  const urlPreset =
    opts.presetFromUrl && rows.some((p) => p.id === opts.presetFromUrl) ? opts.presetFromUrl : "";
  const qAsPreset =
    opts.hubPrefill && rows.some((p) => p.id === opts.hubPrefill) ? opts.hubPrefill : "";
  const presetId =
    urlPreset ||
    qAsPreset ||
    rows.find((p) => p.id === opts.defaultPreset)?.id ||
    rows[0]?.id ||
    "";
  const row = rows.find((p) => p.id === presetId);
  const query = qAsPreset
    ? row?.prompt_ko || opts.hubPrefill
    : opts.hubPrefill || row?.prompt_ko || "";
  return { presetId, query };
}

type Props = {
  embedHero?: boolean;
};

export function LogosResearchStudioClient({ embedHero = false }: Props) {
  const searchParams = useSearchParams();
  const hubPrefill = searchParams.get("q")?.trim() ?? "";
  const presetFromUrl = searchParams.get("preset")?.trim() ?? "";
  const audienceModeFromUrl = parseLogosStudioAudienceMode(searchParams.get("mode"));
  const demoFromUrl = searchParams.get("demo") === "1";
  const autorun = searchParams.get("autorun") === "1" || demoFromUrl;
  const legacyLayout = searchParams.get("legacy") === "1";
  const canvasLayout = !embedHero && !legacyLayout;
  const phaseInit = useMemo(
    () => ({ canvasLayout, embedHero, autorun, legacyLayout }),
    [autorun, canvasLayout, embedHero, legacyLayout],
  );
  const [studioPhase, setStudioPhase] = useState<LogosStudioPhase>(() =>
    resolveInitialStudioPhase(phaseInit),
  );
  const studio = "studio" in logosResearchCopy ? logosResearchCopy.studio : null;
  const [presets, setPresets] = useState<PresetRow[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(true);
  const [presetId, setPresetId] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [queryPipeline, setQueryPipeline] = useState(createLogosQueryPipeline);
  const [error, setError] = useState<string | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [presetMatch, setPresetMatch] = useState<string | null>(null);
  const [presetGuard, setPresetGuard] = useState<{
    action: string;
    message_ko?: string;
    requested_preset_id?: string;
    routed_preset_id?: string;
  } | null>(null);
  const resultRef = useRef<HTMLElement | null>(null);
  const autorunDoneRef = useRef(false);

  const [leadEmail, setLeadEmail] = useState("");
  const [leadOrg, setLeadOrg] = useState("");
  const [leadNote, setLeadNote] = useState("");
  const [leadState, setLeadState] = useState<LeadState>("idle");
  const [leadMessage, setLeadMessage] = useState("");
  const [gapFocusLabel, setGapFocusLabel] = useState<string | null>(null);
  const [presetSlotFilter, setPresetSlotFilter] = useState<string>("all");
  const [quotaDisabled, setQuotaDisabled] = useState(false);
  const [audienceMode, setAudienceMode] = useState<LogosStudioAudienceMode>(audienceModeFromUrl);
  const [showOnboarding, setShowOnboarding] = useState(false);

  const audienceCopy =
    studio && "audience_modes" in studio
      ? (studio as { audience_modes?: Record<string, string> }).audience_modes
      : undefined;

  const defaultPreset = useMemo(
    () => studio?.default_preset_id ?? defaultPresetIdForAudienceMode(audienceMode),
    [audienceMode, studio?.default_preset_id],
  );

  const quotaLow = remaining != null && remaining <= 2 && !embedHero;
  const quotaExceeded = !quotaDisabled && error === "quota_exceeded";
  const demoPresetEligible = presetId ? isEmbedDemoPreset(presetId) : false;
  const demoModeHref = buildStudioDemoUrl(presetId, query);
  const queryRunDisabled = loading || presetsLoading || !query.trim() || quotaExceeded;

  const omniQuickPresets = useMemo(() => {
    const ids = new Set<string>(LOGOS_STUDIO_OMNI_QUICK_PRESET_IDS);
    return LOGOS_STUDIO_OMNI_QUICK_PRESET_IDS.map((id) => presets.find((p) => p.id === id))
      .filter((row): row is PresetRow => !!row && ids.has(row.id));
  }, [presets]);

  const onOmniQuickPreset = useCallback(
    (id: string) => {
      const row = presets.find((p) => p.id === id);
      if (!row) return;
      setPresetId(id);
      setQuery(row.prompt_ko);
      setError(null);
    },
    [presets],
  );

  useEffect(() => {
    if (!canvasLayout) return;
    const page = document.querySelector(".logos-research-page.logos-research-studio-theme");
    if (!page) return;
    page.setAttribute("data-logos-studio-phase", studioPhase);
    return () => {
      page.removeAttribute("data-logos-studio-phase");
    };
  }, [canvasLayout, studioPhase]);

  useEffect(() => {
    setStudioPhase(resolveInitialStudioPhase(phaseInit));
  }, [phaseInit]);

  const presetsForMode = useMemo(
    () => filterPresetsByAudienceMode(presets, audienceMode),
    [audienceMode, presets],
  );

  const presetSlotOptions = useMemo(() => {
    if (audienceMode === "pastoral") {
      return presetsForMode.length > 0 ? [LOGOS_PASTORAL_SLOT_LABEL_KO] : [];
    }
    const labels = new Set<string>();
    for (const row of presetsForMode) {
      if (row.slot_label_ko?.trim()) labels.add(row.slot_label_ko.trim());
    }
    return [...labels].sort((a, b) => a.localeCompare(b, "ko"));
  }, [audienceMode, presetsForMode]);

  const filteredPresets = useMemo(() => {
    if (presetSlotFilter === "all" || audienceMode === "pastoral") return presetsForMode;
    return presetsForMode.filter((p) => p.slot_label_ko?.trim() === presetSlotFilter);
  }, [audienceMode, presetSlotFilter, presetsForMode]);

  const onAudienceModeChange = useCallback(
    (mode: LogosStudioAudienceMode) => {
      setAudienceMode(mode);
      setPresetSlotFilter(mode === "pastoral" ? LOGOS_PASTORAL_SLOT_LABEL_KO : "all");
      setResult(null);
      setPresetMatch(null);
      setError(null);
      autorunDoneRef.current = false;
      const pool = filterPresetsByAudienceMode(presets, mode);
      const fallbackId = defaultPresetIdForAudienceMode(mode);
      const nextId = pool.some((p) => p.id === presetId)
        ? presetId
        : pool.find((p) => p.id === fallbackId)?.id || pool[0]?.id || "";
      if (nextId) {
        const row = pool.find((p) => p.id === nextId);
        setPresetId(nextId);
        if (row) setQuery(row.prompt_ko);
      }
    },
    [presetId, presets],
  );

  useEffect(() => {
    setAudienceMode(audienceModeFromUrl);
  }, [audienceModeFromUrl]);

  useEffect(() => {
    if (
      !canvasLayout ||
      studioPhase !== "omni" ||
      autorun ||
      hubPrefill ||
      presetFromUrl ||
      presetsLoading
    ) {
      setShowOnboarding(false);
      return;
    }
    setShowOnboarding(shouldShowLogosStudioOnboarding());
  }, [autorun, canvasLayout, hubPrefill, presetFromUrl, presetsLoading, studioPhase]);

  const applyOnboarding = useCallback(
    (payload: LogosStudioOnboardingResult) => {
      markLogosStudioOnboardingComplete();
      setShowOnboarding(false);
      onAudienceModeChange(payload.audienceMode);
      const row = presets.find((p) => p.id === payload.topic.preset_id);
      if (row) {
        setPresetId(row.id);
        setQuery(row.prompt_ko);
        if (payload.topic.slot_label_ko && payload.audienceMode === "academic") {
          setPresetSlotFilter(payload.topic.slot_label_ko);
        }
      }
    },
    [onAudienceModeChange, presets],
  );

  const skipOnboarding = useCallback(() => {
    markLogosStudioOnboardingComplete();
    setShowOnboarding(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setPresetsLoading(true);
    (async () => {
      try {
        const data = await fetchStudioJson("/api/logos-research/presets");
        if (cancelled) return;
        if (data.ok !== true) throw new Error(String(data.error || "presets_failed"));
        const rows = (data.presets || []) as PresetRow[];
        setPresets(rows);
        const pool = filterPresetsByAudienceMode(rows, audienceModeFromUrl);
        const initial = resolveInitialPresetSelection(pool, {
          presetFromUrl,
          hubPrefill,
          defaultPreset: defaultPresetIdForAudienceMode(audienceModeFromUrl),
        });
        setPresetId(initial.presetId);
        const omniIdle =
          canvasLayout &&
          resolveInitialStudioPhase({
            canvasLayout,
            embedHero,
            autorun,
            legacyLayout,
          }) === "omni" &&
          !hubPrefill &&
          !presetFromUrl;
        setQuery(omniIdle ? "" : initial.query);
        if (data.quota_disabled === true) {
          setQuotaDisabled(true);
          setError(null);
        }
        if (typeof data.remaining === "number") setRemaining(data.remaining);
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "presets_load_failed");
          setPresets([]);
        }
      } finally {
        if (!cancelled) setPresetsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [audienceModeFromUrl, autorun, canvasLayout, embedHero, hubPrefill, legacyLayout, presetFromUrl]);

  const onPresetChange = useCallback(
    (id: string) => {
      setPresetId(id);
      const row = presets.find((p) => p.id === id);
      if (row) setQuery(row.prompt_ko);
    },
    [presets],
  );

  useEffect(() => {
    if (presetSlotFilter === "all" || !presetId || audienceMode === "pastoral") return;
    const row = presetsForMode.find((p) => p.id === presetId);
    if (row?.slot_label_ko?.trim() !== presetSlotFilter) {
      const next = filteredPresets[0];
      if (next) onPresetChange(next.id);
    }
  }, [audienceMode, filteredPresets, onPresetChange, presetId, presetSlotFilter, presetsForMode]);

  const runQuery = useCallback(async () => {
    if (canvasLayout && studioPhase === "omni") {
      setStudioPhase("workspace");
    }
    const trimmed = query.trim();
    let pipeline = resetLogosQueryPipeline();
    if (!trimmed) {
      pipeline = patchLogosQueryPipeline(pipeline, "query_nonempty", "fail");
      setQueryPipeline(pipeline);
      setError("질문을 입력하세요.");
      return;
    }
    pipeline = patchLogosQueryPipeline(pipeline, "query_nonempty", "ok");
    pipeline = patchLogosQueryPipeline(pipeline, "path_engine", "active");
    setQueryPipeline(pipeline);
    setLoading(true);
    setError(null);
    setPresetGuard(null);
    try {
      const data = await fetchStudioJson("/api/logos-research/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          preset_id: presetId || undefined,
          query,
          embed_demo:
            embedHero || (demoFromUrl && presetId && isEmbedDemoPreset(presetId)) || undefined,
        }),
      });
      if (data.ok !== true) throw new Error(String(data.error || "query_failed"));
      pipeline = patchLogosQueryPipeline(pipeline, "path_engine", "ok");
      pipeline = patchLogosQueryPipeline(pipeline, "citation_lock", "active");
      setRemaining(typeof data.remaining === "number" ? data.remaining : null);
      setPresetMatch(typeof data.match === "string" ? data.match : null);
      if (data.preset_guard && typeof data.preset_guard === "object") {
        setPresetGuard(data.preset_guard as typeof presetGuard);
      }
      const nextResult = data.result as QueryResult;
      setResult(nextResult);
      if (data.quota_disabled === true) setQuotaDisabled(true);
      if (nextResult.preset_id) setPresetId(nextResult.preset_id);
      const hasPath = Boolean(nextResult.path?.verse_refs?.length);
      pipeline = patchLogosQueryPipeline(
        pipeline,
        "citation_lock",
        hasPath ? "ok" : "warn",
      );
      pipeline = patchLogosQueryPipeline(pipeline, "result_ready", "ok");
      setQueryPipeline(pipeline);
      void postStudioTelemetry({
        event: "logos_research_query_success_v1",
        page_path: "/logos-research/studio",
        source_surface: "logos_studio_query",
        effective_level: nextResult.query_mode || "preset",
        access_gate: "research_only_hold",
        response_len: nextResult.answer?.length ?? 0,
        ecs_v1: nextResult.evidence_confidence?.ecs_v1 ?? null,
        ecs_band: nextResult.evidence_confidence?.band ?? null,
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "query_failed";
      setError(msg);
      if (msg === "quota_exceeded") setRemaining(0);
      setResult(null);
      setPresetMatch(null);
      setPresetGuard(null);
      setQueryPipeline((prev) => {
        let next = patchLogosQueryPipeline(prev, "path_engine", "fail");
        next = patchLogosQueryPipeline(next, "citation_lock", "skipped");
        next = patchLogosQueryPipeline(next, "result_ready", "skipped");
        return next;
      });
    } finally {
      setLoading(false);
    }
  }, [canvasLayout, demoFromUrl, embedHero, presetId, query, studioPhase]);

  useEffect(() => {
    if (!autorun || presetsLoading || autorunDoneRef.current) return;
    if (!presetId || !query.trim() || result || loading) return;
    autorunDoneRef.current = true;
    void runQuery();
  }, [autorun, loading, presetId, presetsLoading, query, result, runQuery]);

  useEffect(() => {
    if (!result) return;
    resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [result]);

  useEffect(() => {
    if (!loading) return;
    const id = window.setTimeout(() => {
      setLoading(false);
      setError((prev) => prev || "query_timeout — API 지연. :3203 사용 또는 dev:studio:clean");
    }, STUDIO_LOADING_TIMEOUT_MS);
    return () => window.clearTimeout(id);
  }, [loading]);

  useEffect(() => {
    if (!presetsLoading) return;
    const id = window.setTimeout(() => {
      setPresetsLoading(false);
      setError((prev) => prev || "presets_timeout — dev 서버 .next 깨짐. dev:studio:clean");
    }, STUDIO_LOADING_TIMEOUT_MS);
    return () => window.clearTimeout(id);
  }, [presetsLoading]);

  const reloadPresets = useCallback(() => {
    autorunDoneRef.current = false;
    setPresetId("");
    setQuery("");
    setPresets([]);
    setPresetsLoading(true);
    setError(null);
    void (async () => {
      try {
        const data = await fetchStudioJson("/api/logos-research/presets");
        if (data.ok !== true) throw new Error(String(data.error || "presets_failed"));
        const rows = (data.presets || []) as PresetRow[];
        setPresets(rows);
        const pool = filterPresetsByAudienceMode(rows, audienceMode);
        const initial = resolveInitialPresetSelection(pool, {
          presetFromUrl,
          hubPrefill,
          defaultPreset: defaultPresetIdForAudienceMode(audienceMode),
        });
        setPresetId(initial.presetId);
        const omniIdle =
          canvasLayout &&
          resolveInitialStudioPhase({
            canvasLayout,
            embedHero,
            autorun,
            legacyLayout,
          }) === "omni" &&
          !hubPrefill &&
          !presetFromUrl;
        setQuery(omniIdle ? "" : initial.query);
        if (data.quota_disabled === true) {
          setQuotaDisabled(true);
          setError(null);
        }
        if (typeof data.remaining === "number") setRemaining(data.remaining);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "presets_load_failed");
      } finally {
        setPresetsLoading(false);
      }
    })();
  }, [audienceMode, canvasLayout, embedHero, autorun, legacyLayout, hubPrefill, presetFromUrl]);

  const submitLead = useCallback(async () => {
    setLeadState("submitting");
    setLeadMessage("");
    try {
      const res = await fetch("/api/logos-research/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: leadEmail,
          organization: leadOrg,
          tier: "pilot",
          note: leadNote,
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "lead_failed");
      setLeadState("ok");
      setLeadMessage(data.lead_id || "submitted");
    } catch (e: unknown) {
      setLeadState("error");
      setLeadMessage(e instanceof Error ? e.message : "lead_failed");
    }
  }, [leadEmail, leadNote, leadOrg]);

  const exportJson = useCallback(() => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `logos_path_${result.preset_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result]);

  const subgraphResult = result
    ? {
        preset_id: result.preset_id,
        query: result.query,
        answer: result.answer,
        query_mode: result.query_mode,
        highlight_node_ids: result.highlight_node_ids,
        path: result.path,
        synthesis_meta: result.synthesis_meta,
        conflict_context: result.conflict_context ?? undefined,
        graphrag_meta: result.graphrag_meta,
        evidence_confidence: result.evidence_confidence,
        insight_card: result.insight_card,
      }
    : null;

  const queryFormFields = (
    <>
      <h2 id="lr-studio-run-title" className="lr-studio-canvas-chat-title">
        {studio?.title ?? "경로 질의"}
      </h2>
      {canvasLayout ? (
        <div
          className="lr-studio-audience-modes"
          role="group"
          aria-label={audienceCopy?.group_label ?? "사용 맥락"}
          data-logos-audience-mode={audienceMode}
        >
          <span className="lr-studio-audience-modes-label">{audienceCopy?.group_label ?? "사용 맥락"}</span>
          {LOGOS_STUDIO_AUDIENCE_MODES.map((mode) => (
            <button
              key={mode}
              type="button"
              className={`lr-studio-audience-mode-chip${audienceMode === mode ? " lr-studio-audience-mode-chip--active" : ""}`}
              aria-pressed={audienceMode === mode}
              onClick={() => onAudienceModeChange(mode)}
            >
              {mode === "pastoral"
                ? (audienceCopy?.pastoral ?? "묵상·고민")
                : (audienceCopy?.academic ?? "학술 연구")}
            </button>
          ))}
        </div>
      ) : null}
      {canvasLayout && audienceMode === "pastoral" ? (
        <p className="lr-studio-pastoral-disclaimer" role="note" data-logos-pastoral-disclaimer="1">
          {audienceCopy?.pastoral_disclaimer ??
            "[research_only] 성경 텍스트·경로 관측 도구입니다. 목회 상담·심리 치료·의료 조언이 아닙니다."}
        </p>
      ) : null}
      <p className="lr-section-lead lr-studio-run-lead">
        {audienceMode === "pastoral"
          ? (audienceCopy?.pastoral_lead ??
              "개인적 고민을 성경 구절·경로로 읽는 관측 모드입니다. 상담·치료가 아닙니다.")
          : (studio?.lead ?? "질문을 입력하면 GraphRAG가 구절·경로를 조립합니다.")}
      </p>

      <div className="lr-studio-form lr-studio-form--grid">
        <label className="lr-studio-label" htmlFor="lr-preset">
          {studio?.label_preset ?? "프리셋"}
        </label>
        {presetSlotOptions.length > 0 ? (
          <div
            className="lr-studio-preset-slot-filters"
            role="group"
            aria-label="프리셋 분류"
            data-logos-preset-slot-filters="1"
          >
            <button
              type="button"
              className={`lr-studio-preset-slot-chip${presetSlotFilter === "all" ? " lr-studio-preset-slot-chip--active" : ""}`}
              onClick={() => setPresetSlotFilter("all")}
            >
              전체
            </button>
            {presetSlotOptions.map((label) => (
              <button
                key={label}
                type="button"
                className={`lr-studio-preset-slot-chip${presetSlotFilter === label ? " lr-studio-preset-slot-chip--active" : ""}`}
                onClick={() => setPresetSlotFilter(label)}
              >
                {label}
              </button>
            ))}
          </div>
        ) : null}
        <select
          id="lr-preset"
          className="lr-studio-input"
          value={presetId}
          onChange={(e) => onPresetChange(e.target.value)}
          disabled={presetsLoading || filteredPresets.length === 0}
        >
          {presetsLoading ? (
            <option value="">{studio?.loading ?? "프리셋 불러오는 중…"}</option>
          ) : filteredPresets.length === 0 ? (
            <option value="">선택 분류에 프리셋 없음</option>
          ) : (
            filteredPresets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.slot_label_ko ? `[${p.slot_label_ko}] ` : ""}
                {p.prompt_ko.slice(0, 72)}
                {p.prompt_ko.length > 72 ? "…" : ""}
              </option>
            ))
          )}
        </select>

        <label className="lr-studio-label" htmlFor="lr-query">
          {studio?.label_question ?? "질문"}
        </label>
        <textarea
          id="lr-query"
          className="lr-studio-textarea"
          rows={canvasLayout ? 4 : 3}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        {!embedHero && !quotaDisabled ? (
          <div
            className={`lr-studio-quota-banner${quotaLow ? " lr-studio-quota-banner--low" : ""}${quotaExceeded ? " lr-studio-quota-banner--exceeded" : ""}`}
            role="status"
          >
            <span className="lr-studio-quota-banner-label">
              {studio?.quota_remaining ?? "오늘 남은 무료 쿼터"}:{" "}
              <strong>{remaining ?? "…"}</strong> / {LOGOS_FREE_DAILY_QUOTA}
            </span>
            <span className="lr-studio-quota-banner-note">쿠키 기준 · Azure 결제와 무관</span>
          </div>
        ) : null}

        <div className="lr-studio-actions">
          <button
            type="button"
            className="lr-btn lr-btn-primary"
            onClick={runQuery}
            disabled={queryRunDisabled}
          >
            {loading ? (studio?.label_running ?? "실행 중…") : studio?.run_label ?? "경로 질의 실행"}
          </button>
        </div>

        {quotaExceeded ? (
          <div className="lr-studio-quota-recovery" role="alert">
            <p className="lr-studio-quota-recovery-title">
              {studio?.quota_exceeded_title ?? "오늘 무료 8회를 모두 사용했습니다"}
            </p>
            <p className="lr-studio-quota-recovery-body">
              {studio?.quota_exceeded_body ??
                "Azure·결제 오류가 아닙니다. 브라우저 쿠키 기준 1일 8회 한도입니다."}
            </p>
            {demoPresetEligible ? (
              <p className="lr-studio-quota-recovery-cta">
                <Link href={demoModeHref} className="lr-studio-quota-demo-link">
                  {studio?.quota_demo_cta ?? "데모 모드로 계속 (allowlist · 쿼터 제외)"}
                </Link>
              </p>
            ) : null}
            <p className="lr-studio-quota-recovery-hint">
              {studio?.quota_reset_hint ?? "UTC 자정 이후 자동 리셋 · 시크릿 창에서도 재시도 가능"}
            </p>
          </div>
        ) : error && !quotaExceeded ? (
          <p className="lr-studio-error" role="alert">
            {error}{" "}
            <button type="button" className="lr-studio-retry-btn" onClick={reloadPresets}>
              다시 시도
            </button>
          </p>
        ) : null}
        {presetGuard?.action === "auto_route" && presetGuard.message_ko ? (
          <p className="lr-studio-preset-guard" role="status" data-logos-preset-guard="auto_route">
            {presetGuard.message_ko}
          </p>
        ) : null}
      </div>
    </>
  );

  const canvasAnswerBlock =
    result && canvasLayout ? (
      <div className="lr-scriptorium-summary" aria-labelledby="lr-studio-canvas-answer-title">
        {result.query_mode || presetMatch || typeof result.evidence_confidence?.ecs_v1 === "number" ? (
          <p className="lr-scriptorium-summary-meta" role="status">
            {presetMatchLabel(presetMatch ?? undefined) ? (
              <span className="lr-studio-slot-badge lr-studio-slot-badge--router">
                {presetMatchLabel(presetMatch ?? undefined)}
              </span>
            ) : null}
            {typeof result.evidence_confidence?.ecs_v1 === "number" ? (
              <span
                className={`lr-studio-slot-badge lr-studio-slot-badge--ecs lr-studio-slot-badge--ecs-${result.evidence_confidence.band ?? "mid"}`}
                title={ecsV1Tooltip(result.evidence_confidence.note_ko)}
              >
                ECS {result.evidence_confidence.ecs_v1}
              </span>
            ) : null}
          </p>
        ) : null}
        <p id="lr-studio-canvas-answer-title" className="lr-scriptorium-summary-text">
          {buildScriptoriumInquirySummary(result.answer || result.path.note_ko || "")}
        </p>
      </div>
    ) : null;

  const scriptoriumPresetSelect = (
    <>
      {presetSlotOptions.length > 0 && audienceMode === "academic" ? (
        <div
          className="lr-studio-preset-slot-filters lr-scriptorium-slot-filters"
          role="group"
          aria-label="프리셋 분류"
          data-logos-preset-slot-filters="1"
        >
          <button
            type="button"
            className={`lr-studio-preset-slot-chip${presetSlotFilter === "all" ? " lr-studio-preset-slot-chip--active" : ""}`}
            onClick={() => setPresetSlotFilter("all")}
          >
            전체
          </button>
          {presetSlotOptions.map((label) => (
            <button
              key={label}
              type="button"
              className={`lr-studio-preset-slot-chip${presetSlotFilter === label ? " lr-studio-preset-slot-chip--active" : ""}`}
              onClick={() => setPresetSlotFilter(label)}
            >
              {label}
            </button>
          ))}
        </div>
      ) : null}
      <label className="lr-studio-label lr-scriptorium-preset-label" htmlFor="lr-preset">
        프리셋
      </label>
      <select
        id="lr-preset"
        className="lr-studio-input lr-scriptorium-preset-select"
        value={presetId}
        onChange={(e) => onPresetChange(e.target.value)}
        disabled={presetsLoading || filteredPresets.length === 0}
      >
        {presetsLoading ? (
          <option value="">{studio?.loading ?? "프리셋 불러오는 중…"}</option>
        ) : filteredPresets.length === 0 ? (
          <option value="">선택 분류에 프리셋 없음</option>
        ) : (
          filteredPresets.map((p) => (
            <option key={p.id} value={p.id}>
              {p.slot_label_ko ? `[${p.slot_label_ko}] ` : ""}
              {p.prompt_ko.slice(0, 72)}
              {p.prompt_ko.length > 72 ? "…" : ""}
            </option>
          ))
        )}
      </select>
    </>
  );

  const scriptoriumInquiryFooter = (
    <>
      <div
        className="lr-studio-audience-modes lr-scriptorium-audience"
        role="group"
        aria-label={audienceCopy?.group_label ?? "사용 맥락"}
        data-logos-audience-mode={audienceMode}
      >
        {LOGOS_STUDIO_AUDIENCE_MODES.map((mode) => (
          <button
            key={mode}
            type="button"
            className={`lr-studio-audience-mode-chip${audienceMode === mode ? " lr-studio-audience-mode-chip--active" : ""}`}
            aria-pressed={audienceMode === mode}
            onClick={() => onAudienceModeChange(mode)}
          >
            {mode === "pastoral"
              ? (audienceCopy?.pastoral ?? "묵상·고민")
              : (audienceCopy?.academic ?? "학술 연구")}
          </button>
        ))}
      </div>
      {audienceMode === "pastoral" ? (
        <p className="lr-studio-pastoral-disclaimer" role="note" data-logos-pastoral-disclaimer="1">
          {audienceCopy?.pastoral_disclaimer ??
            "[research_only] 성경 텍스트·경로 관측 도구입니다. 목회 상담·심리 치료·의료 조언이 아닙니다."}
        </p>
      ) : null}
      {quotaExceeded || error ? (
        <p className="lr-studio-error lr-scriptorium-error" role="alert">
          {quotaExceeded ? (studio?.quota_exceeded_title ?? "오늘 무료 한도 도달") : error}
        </p>
      ) : null}
    </>
  );

  const scriptoriumVerseChips =
    result && result.path.verse_refs.length ? (
      <div className="lr-scriptorium-inquiry-chip-row">
        {verseRefShortList(result.path.verse_refs, 8).map((ref) => (
          <button
            key={ref}
            type="button"
            className="lr-studio-ref-chip lr-studio-ref-chip--mapped"
            onClick={() => dispatchScriptoriumVerseSelect(ref)}
          >
            {ref}
          </button>
        ))}
      </div>
    ) : null;

  const canvasChatPane = canvasLayout ? (
    <LogosStudioScriptoriumInquiry
      title="연구 질의"
      topicPills={buildScriptoriumTopicPills(
        presetId,
        presets.find((p) => p.id === presetId)?.slot_label_ko,
      )}
      query={query}
      onQueryChange={setQuery}
      onRun={runQuery}
      runLabel={studio?.run_label ?? "질의"}
      running={loading}
      runDisabled={queryRunDisabled}
      presetSelect={scriptoriumPresetSelect}
      summaryBlock={canvasAnswerBlock}
      verseChips={scriptoriumVerseChips}
      footer={scriptoriumInquiryFooter}
    />
  ) : (
    <>
      {queryFormFields}
      {canvasAnswerBlock}
    </>
  );

  return (
    <div
      className={`lr-studio${canvasLayout ? " lr-studio--canvas lr-studio--scriptorium" : ""}${studioPhase === "omni" ? " lr-studio--omni-entry" : " lr-studio--workspace"}`}
      data-logos-studio-phase={canvasLayout ? studioPhase : undefined}
    >
      {canvasLayout && studioPhase === "omni" && showOnboarding ? (
        <LogosStudioOnboardingOverlay onComplete={applyOnboarding} onSkip={skipOnboarding} />
      ) : null}
      {canvasLayout && studioPhase === "omni" ? (
        <LogosStudioOmniEntry
          title={
            (studio as { omni_title?: string } | null)?.omni_title ?? "무엇을 연구할까요?"
          }
          lead={
            (studio as { omni_lead?: string } | null)?.omni_lead ??
            "질문·구절·주제를 입력하세요."
          }
          placeholder={
            (studio as { omni_placeholder?: string } | null)?.omni_placeholder ??
            "연구 질문을 입력하세요…"
          }
          governanceNote={
            (studio as { omni_governance?: string } | null)?.omni_governance ??
            "research_only · citation lock · send_gate HOLD"
          }
          query={query}
          onQueryChange={setQuery}
          onRun={runQuery}
          runLabel={studio?.run_label ?? "경로 질의 실행"}
          running={loading}
          runDisabled={queryRunDisabled}
          quickPresets={omniQuickPresets}
          onQuickPreset={onOmniQuickPreset}
          error={error}
          quotaRemaining={remaining}
          quotaTotal={LOGOS_FREE_DAILY_QUOTA}
          showQuota={!embedHero && !quotaDisabled}
          pipelineStages={queryPipeline}
        />
      ) : canvasLayout ? (
        <LogosCanvasStudioLayout
          chat={canvasChatPane}
          loading={loading}
          result={subgraphResult}
          conflictContext={result?.conflict_context ?? undefined}
          autorun={autorun}
          activePresetId={result?.preset_id ?? presetId}
          onGapChipClick={(chip) =>
            setGapFocusLabel(chip.bridge_question_ko || chip.label_ko || null)
          }
          gapFocusLabel={gapFocusLabel}
          audienceMode={audienceMode}
          headerActions={
            result ? (
              <button type="button" className="lr-btn lr-btn-ghost lr-studio-export-top" onClick={exportJson}>
                {studio?.export_json ?? "JSON"}
              </button>
            ) : null
          }
        />
      ) : null}

      {!canvasLayout && !embedHero ? (
      <section className="lr-studio-panel lr-studio-panel--run" aria-labelledby="lr-studio-run-title">
        {queryFormFields}
      </section>
      ) : null}

      {embedHero && error ? (
        <p className="lr-studio-error lr-studio-error--embed" role="alert">
          {error}
        </p>
      ) : null}

      {!canvasLayout && loading && autorun && !result ? (
        <section className="lr-studio-panel lr-studio-panel--alt lr-studio-panel--pending" aria-busy="true">
          <p className="lr-studio-pending">{studio?.label_running ?? "경로 엔진 실행 중…"}</p>
          <div className="lr-studio-graph-skeleton" aria-hidden="true" />
        </section>
      ) : null}

      {!canvasLayout && result ? (
        <section
          ref={resultRef}
          className="lr-studio-panel lr-studio-panel--result"
          aria-labelledby="lr-studio-result"
        >
          <header className="lr-studio-result-head">
            <div>
              <h2 id="lr-studio-result">{studio?.result_title ?? "통찰 경로"}</h2>
              {presetGuard?.action === "auto_route" && presetGuard.message_ko ? (
                <p className="lr-studio-preset-guard" role="status" data-logos-preset-guard="auto_route">
                  {presetGuard.message_ko}
                </p>
              ) : null}
              {result.query_mode || presetMatch ? (
                <p className="lr-studio-query-mode" role="status">
                  {presetMatchLabel(presetMatch ?? undefined) ? (
                    <span className="lr-studio-slot-badge lr-studio-slot-badge--router">
                      {presetMatchLabel(presetMatch ?? undefined)}
                    </span>
                  ) : null}
                  {result.query_mode ? (
                    <span className="lr-studio-slot-badge">{graphragModeLabel(result.query_mode)}</span>
                  ) : null}
                  {result.graphrag_meta?.bridges_matched != null
                    ? ` · bridge ${result.graphrag_meta.bridges_matched}`
                    : ""}
                  {result.path.verse_refs.length
                    ? ` · 구절 ${result.path.verse_refs.length}`
                    : ""}
                  {typeof result.evidence_confidence?.ecs_v1 === "number" ? (
                    <span
                      className={`lr-studio-slot-badge lr-studio-slot-badge--ecs lr-studio-slot-badge--ecs-${result.evidence_confidence.band ?? "mid"}`}
                      title={ecsV1Tooltip(result.evidence_confidence.note_ko)}
                    >
                      ECS {result.evidence_confidence.ecs_v1}
                    </span>
                  ) : null}
                </p>
              ) : null}
            </div>
            <button type="button" className="lr-btn lr-btn-ghost lr-studio-export-top" onClick={exportJson}>
              {studio?.export_json ?? "JSON"}
            </button>
          </header>

          <div className="lr-studio-result-stack">
            <LogosResearchSubgraphPanel
              result={{
                preset_id: result.preset_id,
                query: result.query,
                answer: result.answer,
                query_mode: result.query_mode,
                highlight_node_ids: result.highlight_node_ids,
                path: result.path,
                synthesis_meta: result.synthesis_meta,
                conflict_context: result.conflict_context ?? undefined,
                graphrag_meta: result.graphrag_meta,
                evidence_confidence: result.evidence_confidence,
                insight_card: result.insight_card,
              }}
              autoDemoOnMount={autorun && !embedHero}
              productDemoMode={embedHero}
            />

            {result.conflict_context?.ok && result.conflict_context.group_count > 0 ? (
              <LogosResearchConflictSidecarPanel context={result.conflict_context} />
            ) : null}

            {!embedHero ? (
              <>
                <LogosResearchSasangNetworkKpiStrip />
                <LogosResearchInsightLatticePanel
                  activePresetId={result.preset_id}
                  onGapChipClick={(chip) => setGapFocusLabel(chip.bridge_question_ko || chip.label_ko)}
                />
                <LogosResearchSasangNetworkSummaryPanel />
                {gapFocusLabel ? (
                  <p className="lr-studio-gap-focus" role="status">
                    {gapFocusLabel}
                  </p>
                ) : null}
              </>
            ) : null}
          </div>
        </section>
      ) : null}

      {!embedHero && !canvasLayout ? (
      <section className="lr-studio-panel" aria-labelledby="lr-studio-lead-title">
        <h2 id="lr-studio-lead-title">{studio?.lead_title ?? "Pro / 기관 파일럿"}</h2>
        <p className="lr-section-lead">
          {studio?.lead_body ??
            "API 키 베타, 상향 쿼터, private slice — 리드 캡처(send_gate HOLD)."}
        </p>
        <div className="lr-studio-form lr-studio-form--grid">
          <input
            className="lr-studio-input"
            type="email"
            placeholder={studio?.placeholder_email ?? "이메일"}
            value={leadEmail}
            onChange={(e) => setLeadEmail(e.target.value)}
            autoComplete="email"
          />
          <input
            className="lr-studio-input"
            type="text"
            placeholder={studio?.placeholder_org ?? "기관명 (선택)"}
            value={leadOrg}
            onChange={(e) => setLeadOrg(e.target.value)}
          />
          <textarea
            className="lr-studio-textarea"
            rows={2}
            placeholder={studio?.placeholder_note ?? "사용 사례 (선택)"}
            value={leadNote}
            onChange={(e) => setLeadNote(e.target.value)}
          />
          <button
            type="button"
            className="lr-btn lr-btn-primary"
            disabled={leadState === "submitting" || !leadEmail.includes("@")}
            onClick={submitLead}
          >
            {leadState === "submitting"
              ? (studio?.label_sending ?? "전송 중…")
              : studio?.lead_cta ?? "파일럿 접근 요청"}
          </button>
          {leadMessage ? <p className="lr-studio-lead-msg">{leadMessage}</p> : null}
        </div>
      </section>
      ) : null}

      {!embedHero && !canvasLayout ? (
      <section className="lr-studio-trust" aria-labelledby="lr-studio-trust-title">
        <h2 id="lr-studio-trust-title">{studio?.trust_title ?? "GitHub에서 검증 (OSS)"}</h2>
        <ul>
          {(studio?.trust_links ?? [
            {
              label: "mkm-universal-root",
              href: "https://github.com/mkmlab-v2/mkm-universal-root",
            },
            {
              label: "B2B pilot spec",
              href: "https://github.com/mkmlab-v2/mkm-universal-root/blob/main/docs/MKM_B2B_PILOT_INQUIRY_SPEC_PUBLIC_v1.md",
            },
          ]).map((link: { label: string; href: string }) => (
            <li key={link.href}>
              <a href={link.href} rel="noopener noreferrer">
                {link.label}
              </a>
            </li>
          ))}
        </ul>
        <p className="lr-studio-bench-note">
          {studio?.bench_note ??
            "UR-Bench-5K: B0·B3를 별도 보고 — 하나의 헤드라인 점수로 합치지 마세요."}
        </p>
      </section>
      ) : null}
    </div>
  );
}
