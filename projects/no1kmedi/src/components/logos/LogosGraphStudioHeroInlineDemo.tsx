"use client";



import Link from "next/link";

import { useCallback, useEffect, useMemo, useState } from "react";



import { LogosResearchStoryboardPanel } from "@/components/logos-research/LogosResearchStoryboardPanel";

import { LogosResearchPathMindmapPanel } from "@/components/logos-research/LogosResearchPathMindmapPanel";

import {

  LOGOS_GRAPH_STUDIO_DEFAULT_PRESET,

  buildLogosGraphStudioEmbedUrl,

} from "@/lib/logosGraphStudioEmbed";

import {

  LOGOS_HERO_DEMO_BEATS_V1,

  LOGOS_HERO_DEMO_LOOP_MS,

  beatAtElapsedMs,

  prefersReducedMotion,

} from "@/lib/logosStudioHeroDemoBeatsV1";

import type { GraphSliceCoverage } from "@/lib/logosStudioGraphCoverageV1";

import type { ConflictContextResult } from "@/lib/logosStudioConflictBridgeV1";

import { useLogosStudioGraphSlice } from "@/lib/useLogosStudioGraphSliceV1";



type QueryResult = {

  preset_id: string;

  query: string;

  answer: string;

  query_mode?: string;

  path: {

    note_ko?: string | null;

    steps?: string[];

    verse_refs: string[];

    bridges_matched?: number | null;

    node_ids?: string[];

    reasoning_path_v1?: { node_ids?: string[] };

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

    requery_poc?: boolean;

  } | null;

  highlight_node_ids?: string[];

};



type Props = {

  title?: string;

  note?: string;

  fallbackHref?: string;

  presetId?: string;

  className?: string;

  autoplayBeats?: boolean;

};



type HeroView = "storyboard" | "mindmap";



const EMPTY_COVERAGE: GraphSliceCoverage = {

  totalVerseRefs: 0,

  mappedVerseRefs: 0,

  ratio: 0,

  mappedNodeIds: [],

  unmappedRefs: [],

};



export function LogosGraphStudioHeroInlineDemo({

  title = "Logos Graph Studio — citation-locked storyboard",

  note,

  fallbackHref,

  presetId = LOGOS_GRAPH_STUDIO_DEFAULT_PRESET,

  className,

  autoplayBeats = true,

}: Props) {

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  const [result, setResult] = useState<QueryResult | null>(null);

  const [elapsedMs, setElapsedMs] = useState(0);

  const [motionReduced, setMotionReduced] = useState(false);

  const [heroView, setHeroView] = useState<HeroView>("storyboard");



  const { graphDoc, hopIndex } = useLogosStudioGraphSlice(heroView === "mindmap");



  const studioHref =

    fallbackHref ??

    buildLogosGraphStudioEmbedUrl({ preset: presetId, embed: true, autoplay: true });



  const fetchDemo = useCallback(async (signal?: AbortSignal) => {

    setLoading(true);

    setError(null);

    try {

      const res = await fetch("/api/logos-research/query", {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({ preset_id: presetId, embed_demo: true }),

        signal,

      });

      const data = await res.json();

      if (!res.ok || !data.ok) throw new Error(String(data.error || "query_failed"));

      setResult(data.result as QueryResult);

    } catch (e: unknown) {

      if (signal?.aborted) return;

      setResult(null);

      setError(e instanceof Error ? e.message : "query_failed");

    } finally {

      if (!signal?.aborted) setLoading(false);

    }

  }, [presetId]);



  useEffect(() => {

    const controller = new AbortController();

    void fetchDemo(controller.signal);

    return () => controller.abort();

  }, [fetchDemo]);



  useEffect(() => {

    setMotionReduced(prefersReducedMotion());

  }, []);



  useEffect(() => {

    if (!autoplayBeats || loading || !result || motionReduced) return;

    const started = performance.now();

    const id = window.setInterval(() => {

      setElapsedMs(Math.floor(performance.now() - started));

    }, 120);

    return () => window.clearInterval(id);

  }, [autoplayBeats, loading, result, motionReduced]);



  const activeBeat = useMemo(() => {

    if (!autoplayBeats || loading || !result || motionReduced) return null;

    return beatAtElapsedMs(elapsedMs);

  }, [autoplayBeats, elapsedMs, loading, motionReduced, result]);



  useEffect(() => {

    if (activeBeat?.slot === "lens") setHeroView("mindmap");

  }, [activeBeat?.slot]);



  const beatProgress = useMemo(() => {

    if (!activeBeat) return 0;

    const span = activeBeat.endMs - activeBeat.startMs;

    const local = elapsedMs % LOGOS_HERO_DEMO_LOOP_MS - activeBeat.startMs;

    return span > 0 ? Math.min(100, Math.max(0, (local / span) * 100)) : 0;

  }, [activeBeat, elapsedMs]);



  const coverage = useMemo((): GraphSliceCoverage => {

    if (!result?.path?.verse_refs?.length) return EMPTY_COVERAGE;

    const refs = result.path.verse_refs;

    return {

      totalVerseRefs: refs.length,

      mappedVerseRefs: refs.length,

      ratio: 1,

      mappedNodeIds: result.highlight_node_ids ?? [],

      unmappedRefs: [],

    };

  }, [result]);



  const meshSeedIds = useMemo(() => {

    const seeds = new Set<string>();

    for (const id of result?.highlight_node_ids ?? []) if (id) seeds.add(id);

    for (const id of result?.path?.node_ids ?? []) if (id) seeds.add(id);

    for (const id of result?.path?.reasoning_path_v1?.node_ids ?? []) if (id) seeds.add(id);

    return [...seeds];

  }, [result]);



  const nodeById = useMemo(() => {

    const map: Record<string, { id: string; label?: string; ref?: string }> = {};

    for (const n of graphDoc?.nodes || []) map[n.id] = n;

    return map;

  }, [graphDoc]);



  const showMindmapPulse = activeBeat?.slot === "lens";



  return (

    <figure

      className={`lr-hero-inline-demo-wrap ${className ?? ""}`}

      data-layer-b-embed="hero-inline"

      data-logos-graph-studio-inline="1"

      data-logos-graph-studio-embed="1"

      aria-label={title}

    >

      <div className="lr-hero-inline-demo-governance" role="note">

        <span>[HYPO]</span>

        <span>NON_GATING</span>

        <span>inline storyboard</span>

        <span>embed_demo</span>

        {activeBeat ? <span className="lr-hero-inline-demo-beat-tag">{activeBeat.labelKo}</span> : null}

      </div>



      {activeBeat ? (

        <div

          className="lr-hero-inline-demo-beat-progress"

          role="progressbar"

          aria-valuenow={Math.round(beatProgress)}

          aria-valuemin={0}

          aria-valuemax={100}

          aria-label={`30s demo beat: ${activeBeat.labelKo}`}

        >

          <span style={{ width: `${beatProgress}%` }} />

        </div>

      ) : null}



      <div className="lr-hero-inline-demo-card lr-hero-inline-demo-card--tabbed" aria-busy={loading || undefined}>

        {loading ? (

          <div className="lr-hero-inline-demo-skeleton" aria-hidden="true">

            <p className="lr-hero-inline-demo-status">

              {LOGOS_HERO_DEMO_BEATS_V1[0].labelKo}…

            </p>

          </div>

        ) : null}



        {error ? (

          <p className="lr-hero-inline-demo-error" role="alert">

            {error}{" "}

            <Link href={studioHref} className="lr-hero-inline-demo-retry">

              Studio에서 열기

            </Link>

          </p>

        ) : null}



        {result && !loading ? (

          <div className="lr-hero-inline-demo-tabbed logos-research-studio-theme">

            <div className="lr-hero-inline-demo-tabs" role="tablist" aria-label="히어로 데모 뷰">

              <button

                type="button"

                role="tab"

                id="lr-hero-tab-storyboard"

                aria-selected={heroView === "storyboard"}

                aria-controls="lr-hero-panel-storyboard"

                className={`lr-hero-inline-demo-tab${heroView === "storyboard" ? " lr-hero-inline-demo-tab--active" : ""}`}

                onClick={() => setHeroView("storyboard")}

              >

                스토리보드

              </button>

              <button

                type="button"

                role="tab"

                id="lr-hero-tab-mindmap"

                aria-selected={heroView === "mindmap"}

                aria-controls="lr-hero-panel-mindmap"

                className={`lr-hero-inline-demo-tab${heroView === "mindmap" ? " lr-hero-inline-demo-tab--active" : ""}`}

                onClick={() => setHeroView("mindmap")}

              >

                경로 마인드맵

              </button>

            </div>



            <div

              id="lr-hero-panel-storyboard"

              role="tabpanel"

              aria-labelledby="lr-hero-tab-storyboard"

              hidden={heroView !== "storyboard"}

              className="lr-hero-inline-demo-panel lr-hero-inline-demo-storyboard"

            >

              <LogosResearchStoryboardPanel

                result={{

                  query: result.query,

                  answer: result.answer,

                  query_mode: result.query_mode,

                  path: result.path,

                  synthesis_meta: result.synthesis_meta,

                  conflict_context: result.conflict_context,

                  graphrag_meta: result.graphrag_meta,

                  evidence_confidence: result.evidence_confidence,

                  insight_card: result.insight_card,

                }}

                coverage={coverage}

                activeSlot={activeBeat?.slot ?? null}

                presetId={presetId}

              />

            </div>



            <div

              id="lr-hero-panel-mindmap"

              role="tabpanel"

              aria-labelledby="lr-hero-tab-mindmap"

              hidden={heroView !== "mindmap"}

              className="lr-hero-inline-demo-panel lr-hero-inline-demo-mindmap"

              data-logos-hero-mini-mindmap="1"

            >

              <LogosResearchPathMindmapPanel

                query={result.query}

                presetId={presetId}

                pathSteps={result.path.steps}

                verseRefs={result.path.verse_refs ?? []}

                meshSummary={{

                  graphDoc,

                  hopIndex,

                  seedIds: meshSeedIds,

                  nodeById,

                }}

                height={280}

                compactMeta

                pulseGraphNodeIds={showMindmapPulse ? result.highlight_node_ids ?? [] : []}

                demoProgress={showMindmapPulse ? beatProgress : 0}

                demoLabel={showMindmapPulse ? activeBeat?.labelKo : undefined}

                demoRunning={showMindmapPulse}

              />

            </div>

          </div>

        ) : null}

      </div>



      {note ? <figcaption className="lr-hero-inline-demo-caption">{note}</figcaption> : null}

      <p className="lr-hero-inline-demo-cta">

        <Link href={studioHref}>Open full Graph Studio →</Link>

      </p>

    </figure>

  );

}


