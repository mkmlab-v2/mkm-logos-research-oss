"use client";

import { useEffect, useMemo, useState } from "react";

const SUMMARY_URL = "/data/logos_studio/sasang_network_summary_v1.json";

type SummaryCard = {
  id: string;
  title: string;
  value: string;
  note?: string;
};

type SummaryDoc = {
  schema?: string;
  send_gate?: string;
  track_a_blocked?: boolean;
  headline?: {
    corpus_verse_count?: number;
    edges_touching_corpus?: number;
    edge_touch_ratio?: number;
    path_count_showroom?: number;
    bloom_chapter_shards?: number;
  };
  cards?: SummaryCard[];
  drilldown?: {
    edge_quality?: {
      edge_total?: number;
      edges_touching_corpus?: number;
      malformed_no_ref_count?: number;
      edge_type_quality?: Array<{
        edge_type?: string;
        total?: number;
        touch_ratio?: number;
        parse_ratio?: number;
        any_parse_ratio?: number;
        single_side_parse_ratio?: number;
        src_parse_ratio?: number;
        dst_parse_ratio?: number;
      }>;
      weakest_parse_edge_types?: Array<{
        edge_type?: string;
        total?: number;
        touch_ratio?: number;
        parse_ratio?: number;
      }>;
    };
  };
};

type EdgeTypeQualityRow = NonNullable<
  NonNullable<NonNullable<SummaryDoc["drilldown"]>["edge_quality"]>["edge_type_quality"]
>[number];

function pctLabel(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`;
}

function EdgeTypeMiniTrend({
  row,
  edgeTotal,
}: {
  row: EdgeTypeQualityRow;
  edgeTotal: number;
}) {
  const total = Number(row.total || 0);
  const touch = Number(row.touch_ratio || 0);
  const parse = Number(row.parse_ratio || 0);
  const singleSide = Number(row.single_side_parse_ratio || 0);
  const volumeShare = edgeTotal > 0 ? total / edgeTotal : 0;
  const touchingEst = Math.round(total * touch);

  const bars = [
    { id: "volume", label: "전체 엣지 대비 비중", value: volumeShare, hint: `${total.toLocaleString()} / ${edgeTotal.toLocaleString()}` },
    { id: "touch", label: "corpus touch 비율", value: touch, hint: `~${touchingEst.toLocaleString()} touching` },
    { id: "parse", label: "양쪽 ref 파싱 비율", value: parse, hint: pctLabel(parse) },
    { id: "single", label: "한쪽만 verse 파싱", value: singleSide, hint: pctLabel(singleSide) },
  ];

  return (
    <div className="lr-sasang-edge-mini-trend" aria-labelledby="lr-sasang-edge-mini-trend-title">
      <p id="lr-sasang-edge-mini-trend-title" className="lr-sasang-edge-mini-trend-title">
        Mini-trend · <strong>{row.edge_type}</strong>
      </p>
      {bars.map((bar) => (
        <div key={bar.id} className="lr-sasang-edge-mini-trend-row">
          <div className="lr-sasang-edge-mini-trend-meta">
            <span>{bar.label}</span>
            <span>{pctLabel(bar.value)}</span>
          </div>
          <div
            className="lr-sasang-edge-mini-trend-track"
            role="progressbar"
            aria-valuenow={Math.round(bar.value * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${bar.label} ${pctLabel(bar.value)}`}
          >
            <div className="lr-sasang-edge-mini-trend-fill" style={{ width: `${Math.min(100, bar.value * 100)}%` }} />
          </div>
          <small className="lr-sasang-edge-mini-trend-hint">{bar.hint}</small>
        </div>
      ))}
    </div>
  );
}

function useSasangNetworkSummaryDoc() {
  const [doc, setDoc] = useState<SummaryDoc | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(SUMMARY_URL, { cache: "force-cache" });
        if (!res.ok) throw new Error(`summary_http_${res.status}`);
        const data = (await res.json()) as SummaryDoc;
        if (!cancelled) {
          setDoc(data);
          setLoadError(null);
        }
      } catch (e: unknown) {
        if (!cancelled) setLoadError(e instanceof Error ? e.message : "summary_failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  return { doc, loadError };
}

export function LogosResearchSasangNetworkKpiStrip() {
  const { doc } = useSasangNetworkSummaryDoc();
  const headline = doc?.headline;
  if (!headline) return null;

  const items = [
    { id: "corpus", label: "Corpus", value: Number(headline.corpus_verse_count || 0).toLocaleString() },
    { id: "edge_touch", label: "Edge touch", value: pctLabel(Number(headline.edge_touch_ratio || 0)) },
    { id: "paths", label: "Showroom paths", value: Number(headline.path_count_showroom || 0).toLocaleString() },
    { id: "bloom", label: "Bloom shards", value: Number(headline.bloom_chapter_shards || 0).toLocaleString() },
  ];

  return (
    <div className="lr-sasang-kpi-strip" role="list" aria-label="Sasang network KPI strip">
      {items.map((item) => (
        <div key={item.id} role="listitem" className="lr-sasang-kpi-strip-item">
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}

export function LogosResearchSasangNetworkSummaryPanel() {
  const { doc, loadError } = useSasangNetworkSummaryDoc();
  const [selectedEdgeType, setSelectedEdgeType] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"volume" | "parse" | "touch">("volume");
  const [touchFilter, setTouchFilter] = useState<"all" | "high" | "mid" | "low">("all");

  const cards = useMemo(() => (doc?.cards || []).slice(0, 4), [doc?.cards]);
  const [activeCardId, setActiveCardId] = useState<string>("edge_touch");
  const edgeQuality = doc?.drilldown?.edge_quality;
  const edgeQualityRows = useMemo(() => {
    const rows = (edgeQuality?.edge_type_quality || []).slice();
    const filtered = rows.filter((row) => {
      const touch = Number(row.touch_ratio || 0);
      if (touchFilter === "high") return touch >= 0.9;
      if (touchFilter === "mid") return touch >= 0.5 && touch < 0.9;
      if (touchFilter === "low") return touch < 0.5;
      return true;
    });
    const sorted = filtered.sort((a, b) => {
      if (sortBy === "parse") return Number(b.parse_ratio || 0) - Number(a.parse_ratio || 0);
      if (sortBy === "touch") return Number(b.touch_ratio || 0) - Number(a.touch_ratio || 0);
      return Number(b.total || 0) - Number(a.total || 0);
    });
    return sorted;
  }, [edgeQuality?.edge_type_quality, sortBy, touchFilter]);
  const selectedEdgeRow =
    edgeQualityRows.find((row) => row.edge_type === selectedEdgeType) || edgeQualityRows[0] || null;
  const activeCard = cards.find((c) => c.id === activeCardId) || cards[0];
  if (loadError || !doc || !cards.length) return null;

  return (
    <div className="lr-studio-lattice" aria-labelledby="lr-sasang-network-summary-title">
      <h3 id="lr-sasang-network-summary-title">Sasang Network Snapshot</h3>
      <p className="lr-studio-lattice-lead">
        B-track only · send_gate HOLD · non-gating observer panel
      </p>
      <div className="lr-studio-gap-chips" role="list">
        {cards.map((card) => (
          <button
            key={card.id}
            type="button"
            role="listitem"
            className={`lr-studio-gap-chip${activeCardId === card.id ? " lr-studio-gap-chip--active" : ""}`}
            onClick={() => setActiveCardId(card.id)}
          >
            <span className="lr-studio-gap-chip-label">{card.title}</span>
            <strong>{card.value}</strong>
            {card.note ? <small className="lr-studio-gap-bridge">{card.note}</small> : null}
          </button>
        ))}
      </div>
      <details className="lr-scriptorium-evidence-drawer" open={activeCard.id === "edge_touch"}>
        <summary>Drill-down · {activeCard.title}</summary>
        {activeCard.id === "edge_touch" && edgeQuality ? (
          <div className="lr-studio-gap-bridge">
            <p>
              edge total {edgeQuality.edge_total?.toLocaleString() ?? 0} · touching{" "}
              {edgeQuality.edges_touching_corpus?.toLocaleString() ?? 0} · malformed(no ref){" "}
              {edgeQuality.malformed_no_ref_count?.toLocaleString() ?? 0}
            </p>
            <ul>
              {(edgeQuality.weakest_parse_edge_types || []).slice(0, 5).map((row) => (
                <li key={row.edge_type}>
                  {row.edge_type}: parse {(Number(row.parse_ratio || 0) * 100).toFixed(1)}% · touch{" "}
                  {(Number(row.touch_ratio || 0) * 100).toFixed(1)}% · n={(row.total || 0).toLocaleString()}
                </li>
              ))}
            </ul>
            {edgeQualityRows.length > 0 ? (
              <>
                <p>
                  edge type table (click to focus):{" "}
                  <strong>{selectedEdgeRow?.edge_type ?? "n/a"}</strong>
                </p>
                <div className="lr-studio-gap-chips" role="group" aria-label="edge table controls">
                  <button
                    type="button"
                    className={`lr-studio-gap-chip${sortBy === "volume" ? " lr-studio-gap-chip--active" : ""}`}
                    onClick={() => setSortBy("volume")}
                  >
                    <span className="lr-studio-gap-chip-label">sort</span>
                    <strong>volume</strong>
                  </button>
                  <button
                    type="button"
                    className={`lr-studio-gap-chip${sortBy === "parse" ? " lr-studio-gap-chip--active" : ""}`}
                    onClick={() => setSortBy("parse")}
                  >
                    <span className="lr-studio-gap-chip-label">sort</span>
                    <strong>parse</strong>
                  </button>
                  <button
                    type="button"
                    className={`lr-studio-gap-chip${sortBy === "touch" ? " lr-studio-gap-chip--active" : ""}`}
                    onClick={() => setSortBy("touch")}
                  >
                    <span className="lr-studio-gap-chip-label">sort</span>
                    <strong>touch</strong>
                  </button>
                  <button
                    type="button"
                    className={`lr-studio-gap-chip${touchFilter === "all" ? " lr-studio-gap-chip--active" : ""}`}
                    onClick={() => setTouchFilter("all")}
                  >
                    <span className="lr-studio-gap-chip-label">filter</span>
                    <strong>all</strong>
                  </button>
                  <button
                    type="button"
                    className={`lr-studio-gap-chip${touchFilter === "high" ? " lr-studio-gap-chip--active" : ""}`}
                    onClick={() => setTouchFilter("high")}
                  >
                    <span className="lr-studio-gap-chip-label">filter</span>
                    <strong>high touch</strong>
                  </button>
                  <button
                    type="button"
                    className={`lr-studio-gap-chip${touchFilter === "mid" ? " lr-studio-gap-chip--active" : ""}`}
                    onClick={() => setTouchFilter("mid")}
                  >
                    <span className="lr-studio-gap-chip-label">filter</span>
                    <strong>mid touch</strong>
                  </button>
                  <button
                    type="button"
                    className={`lr-studio-gap-chip${touchFilter === "low" ? " lr-studio-gap-chip--active" : ""}`}
                    onClick={() => setTouchFilter("low")}
                  >
                    <span className="lr-studio-gap-chip-label">filter</span>
                    <strong>low touch</strong>
                  </button>
                </div>
                <div className="lr-studio-gap-chips" role="list">
                  {edgeQualityRows.map((row) => (
                    <button
                      key={row.edge_type}
                      type="button"
                      role="listitem"
                      className={`lr-studio-gap-chip${selectedEdgeRow?.edge_type === row.edge_type ? " lr-studio-gap-chip--active" : ""}`}
                      onClick={() => setSelectedEdgeType(row.edge_type ?? null)}
                    >
                      <span className="lr-studio-gap-chip-label">{row.edge_type}</span>
                      <strong>n={(row.total || 0).toLocaleString()}</strong>
                      <small className="lr-studio-gap-bridge">
                        parse {(Number(row.parse_ratio || 0) * 100).toFixed(1)}% · touch{" "}
                        {(Number(row.touch_ratio || 0) * 100).toFixed(1)}%
                      </small>
                    </button>
                  ))}
                </div>
                {selectedEdgeRow && edgeQuality.edge_total ? (
                  <EdgeTypeMiniTrend row={selectedEdgeRow} edgeTotal={edgeQuality.edge_total} />
                ) : null}
              </>
            ) : null}
          </div>
        ) : (
          <p className="lr-studio-gap-bridge">{activeCard.note ?? "요약 카드 메타데이터를 확인하세요."}</p>
        )}
      </details>
    </div>
  );
}
