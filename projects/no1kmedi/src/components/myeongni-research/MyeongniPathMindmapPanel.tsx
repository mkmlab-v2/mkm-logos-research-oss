"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { PathMindmapSvgPanel } from "@/components/path-mindmap/PathMindmapSvgPanel";
import { prefersReducedMotion } from "@/lib/logosResearchSubgraphDemoV1";
import {
  activeNodeIdAtBeat,
  buildMyeongniMindmapDemoTimeline,
} from "@/lib/myeongniMindmapDemoV1";
import {
  MYEONGNI_MINDMAP_LEAF_KINDS,
  buildMyeongniPathMindmapModel,
  layoutMyeongniPathMindmapRadial,
  type MyeongniLiteMindmapInput,
} from "@/lib/myeongniPathMindmapV1";

type Props = {
  input: MyeongniLiteMindmapInput;
  presetId?: string;
  pulseNodeId?: string | null;
  height?: number;
  autoDemo?: boolean;
};

const KIND_STYLES = {
  root: { fill: "#1e1b4b", stroke: "#6366f1", text: "#ffffff", r: 36 },
  pillar: { fill: "#eef2ff", stroke: "#6366f1", text: "#312e81", r: 20 },
  luck: { fill: "#f5f3ff", stroke: "#7c3aed", text: "#4c1d95", r: 20 },
  ten_god: { fill: "#fff7ed", stroke: "#ea580c", text: "#9a3412", r: 16 },
  oheng: { fill: "#ecfdf5", stroke: "#059669", text: "#065f46", r: 16 },
  strength: { fill: "#fefce8", stroke: "#ca8a04", text: "#854d0e", r: 16 },
};

export function MyeongniPathMindmapPanel({
  input,
  presetId = "demo",
  pulseNodeId,
  height = 480,
  autoDemo = true,
}: Props) {
  const [focusLabel, setFocusLabel] = useState<string | null>(null);
  const [demoProgress, setDemoProgress] = useState(0);
  const [demoLabel, setDemoLabel] = useState<string | null>(null);
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoPulseId, setDemoPulseId] = useState<string | null>(null);
  const demoStartRef = useRef<number | null>(null);

  const model = useMemo(() => buildMyeongniPathMindmapModel(input), [input]);
  const demoBeats = useMemo(() => buildMyeongniMindmapDemoTimeline(model), [model]);

  const layoutFn = useMemo(
    () => (m: typeof model, w: number, h: number) => layoutMyeongniPathMindmapRadial(m, w, h, presetId),
    [presetId],
  );

  const startDemo = useCallback(() => {
    if (prefersReducedMotion()) return;
    demoStartRef.current = performance.now();
    setDemoRunning(true);
    setDemoProgress(0);
    setDemoLabel(demoBeats[0]?.label ?? null);
    setDemoPulseId(null);
  }, [demoBeats]);

  useEffect(() => {
    if (!autoDemo) return;
    startDemo();
  }, [autoDemo, model.rootId, startDemo]);

  useEffect(() => {
    if (!demoRunning || prefersReducedMotion()) return;
    let raf = 0;
    const tick = () => {
      const t0 = demoStartRef.current ?? performance.now();
      const elapsed = performance.now() - t0;
      let progress = 0;
      let label = demoBeats[0]?.label ?? "";
      for (const b of demoBeats) {
        if (b.at_ms <= elapsed) {
          progress = b.progress;
          label = b.label;
        }
      }
      setDemoProgress(progress);
      setDemoLabel(label);
      setDemoPulseId(activeNodeIdAtBeat(demoBeats, elapsed));
      if (elapsed >= 3000) {
        setDemoRunning(false);
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [demoBeats, demoRunning]);

  const activeIds = useMemo(() => {
    const ids = new Set<string>();
    if (pulseNodeId) ids.add(pulseNodeId);
    if (demoPulseId) ids.add(demoPulseId);
    if (focusLabel) {
      const hit = model.nodes.find((n) => n.label.includes(focusLabel));
      if (hit) ids.add(hit.id);
    }
    return ids;
  }, [demoPulseId, focusLabel, model.nodes, pulseNodeId]);

  return (
    <PathMindmapSvgPanel
      model={model}
      layoutFn={layoutFn}
      kindStyles={KIND_STYLES}
      activeIds={activeIds}
      title="명리 경로 마인드맵"
      meta="四柱 · 대운/세운 · 십성/오행 · [HYPO] NON_GATING · 중기 방향 참고"
      footnote="임상·매매·Track A 게이트 없음 · 풀 리포트 SSOT와 병행"
      svgTitle="Myeongni 경로 마인드맵"
      height={height}
      className="lr-studio-mindmap-wrap mn-studio-mindmap-wrap"
      panelDataAttributes={{
        "data-myeongni-path-mindmap": "1",
        "data-myeongni-mindmap-node-count": String(model.nodes.length),
      }}
      gradientId="mn-mm-bg-glow"
      gradientInner="#eef2ff"
      gradientOuter="#faf5ff"
      leafKinds={[...MYEONGNI_MINDMAP_LEAF_KINDS]}
      onLeafClick={(n) => setFocusLabel(n.label)}
      demoProgress={demoProgress}
      demoLabel={demoLabel ?? undefined}
      demoRunning={demoRunning}
      onReplayDemo={startDemo}
      replayLabel="경로 데모 재생"
    />
  );
}
