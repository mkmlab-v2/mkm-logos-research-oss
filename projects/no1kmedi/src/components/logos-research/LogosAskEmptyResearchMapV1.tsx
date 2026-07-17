"use client";

/** Empty-state "연구 지도" — SAMPLE viz grammar + REAL v0 lemma/degree layer pin (≠ cite · SEND HOLD).
 * Layout honesty: diagram first in ~308px heart; secondary prose in <details> (P0 tower fix).
 */

import { useEffect, useState } from "react";

import {
  lemmaLayerGrammarAttrV0,
  lemmaLayerIsRealV0,
  loadLogosAskLemmaBetweennessLayerV0,
  type LemmaBetweennessLayerV0,
} from "@/lib/logosAskLemmaBetweennessLayerV0";

export function LogosAskEmptyResearchMapV1() {
  const [layer, setLayer] = useState<LemmaBetweennessLayerV0 | null>(null);

  useEffect(() => {
    let cancelled = false;
    void loadLogosAskLemmaBetweennessLayerV0().then((doc) => {
      if (!cancelled) setLayer(doc);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const real = lemmaLayerIsRealV0(layer);
  const grammar = lemmaLayerGrammarAttrV0(layer);
  const spineLabels = (layer?.empty_map_spine?.labels || []).slice(0, 5);
  const bridgeLabels = (layer?.empty_map_spine?.top_bridge_verses || []).slice(0, 4);
  const edgeN = layer?.graph_stats?.subgraph_edge_count ?? 0;
  const nodeN = layer?.graph_stats?.subgraph_node_count ?? 0;
  const topHub = (layer?.hubs?.verses || [])[0];

  return (
    <div
      className="lr-ask-empty-map"
      data-lr-ask-empty-map="1"
      data-lr-ask-sample-topology="1"
      data-lr-ask-lemma-grammar={grammar}
      data-lr-ask-lemma-layer={real ? "real_v0" : layer ? "hold" : "loading"}
      data-lr-ask-lemma-data-class={layer?.data_class || "PENDING"}
      aria-label={
        real
          ? "연구 지도 미리보기 (SAMPLE 위상 + REAL lemma/degree v0 · 인용 아님 · SEND HOLD)"
          : "연구 지도 미리보기 (샘플 · 인용 아님 · lemma live HOLD)"
      }
    >
      <header className="lr-ask-empty-map-head">
        <p className="lr-ask-empty-map-eyebrow">
          {real ? "preview · SAMPLE + REAL v0" : "preview · sample"}
        </p>
        <h3 className="lr-ask-empty-map-title">연구 지도</h3>
      </header>

      {/* Quiet SAMPLE/REAL chips — Trust grammar stays; no loud corner stack */}
      <ul className="lr-ask-empty-map-grammar lr-ask-empty-map-grammar--quiet" aria-label="SAMPLE 대 REAL/HOLD 문법">
        <li data-grammar="sample">
          <span className="lr-ask-empty-map-grammar-k">SAMPLE</span>
          <span className="lr-ask-empty-map-grammar-v">위상</span>
        </li>
        <li data-grammar={real ? "real" : "hold"}>
          <span className="lr-ask-empty-map-grammar-k">{real ? "REAL v0" : "HOLD"}</span>
          <span className="lr-ask-empty-map-grammar-v">{real ? "lemma" : "lemma"}</span>
        </li>
      </ul>

      {/* Diagram first — heart ~308px must show SVG without scroll */}
      <div className="lr-ask-empty-map-viz" aria-hidden="true">
        <svg
          className="lr-ask-empty-map-svg"
          viewBox="0 0 280 160"
          xmlns="http://www.w3.org/2000/svg"
          role="presentation"
        >
          <defs>
            <linearGradient id="lrAskGhostEdge" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--lr-ask-accent-scholar)" stopOpacity="0.15" />
              <stop offset="50%" stopColor="var(--lr-ask-accent-scholar)" stopOpacity="0.55" />
              <stop offset="100%" stopColor="var(--lr-ask-accent-scholar)" stopOpacity="0.15" />
            </linearGradient>
          </defs>
          <g className="lr-ask-empty-map-grid" opacity="0.22">
            {Array.from({ length: 6 }).map((_, i) => (
              <line
                key={`h-${i}`}
                x1="12"
                y1={24 + i * 22}
                x2="268"
                y2={24 + i * 22}
                stroke="var(--lr-ask-line)"
                strokeWidth="0.75"
              />
            ))}
            {Array.from({ length: 8 }).map((_, i) => (
              <line
                key={`v-${i}`}
                x1={20 + i * 32}
                y1="16"
                x2={20 + i * 32}
                y2="148"
                stroke="var(--lr-ask-line)"
                strokeWidth="0.6"
              />
            ))}
          </g>
          <path
            className="lr-ask-empty-map-edge lr-ask-empty-map-edge--path"
            d="M36 118 C 70 40, 110 40, 140 78 S 210 130, 248 52"
            fill="none"
            stroke="url(#lrAskGhostEdge)"
            strokeWidth="2.2"
            strokeLinecap="round"
          />
          <text x="82" y="72" className="lr-ask-empty-map-midlabel" textAnchor="middle">
            1
          </text>
          <text x="175" y="98" className="lr-ask-empty-map-midlabel" textAnchor="middle">
            2
          </text>
          <path
            className="lr-ask-empty-map-edge lr-ask-empty-map-edge--related"
            d="M48 96 C 90 88, 120 110, 168 92"
            fill="none"
            stroke="var(--lr-ask-line)"
            strokeWidth="1.1"
            strokeDasharray="3 4"
            opacity="0.7"
          />
          <path
            className={`lr-ask-empty-map-edge ${real ? "lr-ask-empty-map-edge--lemma-real" : "lr-ask-empty-map-edge--lemma-sample"}`}
            d="M140 78 C 170 48, 200 44, 232 56"
            fill="none"
            stroke="var(--lr-ask-accent-scholar)"
            strokeWidth="1.35"
            strokeDasharray={real ? "4 3" : "1.5 5"}
            opacity={real ? 0.75 : 0.55}
          />
          <circle className="lr-ask-empty-map-node lr-ask-empty-map-node--query" cx="36" cy="118" r="7" />
          <circle
            className={`lr-ask-empty-map-node ${real ? "lr-ask-empty-map-node--hub-real" : "lr-ask-empty-map-node--hub-sample"}`}
            cx="140"
            cy="78"
            r="9"
          />
          <circle className="lr-ask-empty-map-node" cx="168" cy="92" r="4.5" />
          <circle className="lr-ask-empty-map-node lr-ask-empty-map-node--wedge" cx="248" cy="52" r="8" />
          <text x="28" y="142" className="lr-ask-empty-map-caption">
            질의
          </text>
          <text x="118" y="68" className="lr-ask-empty-map-caption lr-ask-empty-map-caption--hub">
            {real ? "hub REAL" : "hub 샘플"}
          </text>
          <text x="228" y="38" className="lr-ask-empty-map-caption lr-ask-empty-map-caption--wedge">
            1 wedge
          </text>
        </svg>
        {/* Corner tags: quieter; full SAMPLE string retained for Trust gate / sr */}
        <p className="lr-ask-empty-map-sample-tag lr-ask-empty-map-tag--quiet">SAMPLE · not a cite</p>
        <p
          className={`${real ? "lr-ask-empty-map-real-tag" : "lr-ask-empty-map-hold-tag"} lr-ask-empty-map-tag--quiet`}
        >
          {real ? "REAL v0 · HOLD" : "HOLD"}
        </p>
      </div>

      {/* Trust 1-wedge: single HOLD pin above fold */}
      <ul className="lr-ask-empty-map-trust lr-ask-empty-map-trust--one-wedge" aria-label="신뢰 핀">
        <li data-pin="hold">
          <span className="lr-ask-empty-map-pin-label">send_gate</span>
          <span className="lr-ask-empty-map-pin-state">HOLD</span>
        </li>
      </ul>

      <p className="lr-ask-empty-map-cta">질문하면 같은 spine에 실경로가 채워집니다.</p>

      {/* Secondary copy collapsed — kills ~900px empty-map tower */}
      <details className="lr-ask-empty-map-more">
        <summary className="lr-ask-empty-map-more-summary">맵 설명 · REAL 층 · 레전드</summary>
        <p className="lr-ask-empty-map-lead">
          답변 후 같은 spine 언어로 경로·typed-edge가 채워집니다. 위 SVG는{" "}
          <strong className="lr-ask-empty-map-te">SAMPLE 위상</strong>
          이며 근거 구절이 아닙니다.{" "}
          {real ? (
            <>
              <strong className="lr-ask-empty-map-real">REAL v0</strong> = reading-pack 경로 +
              lemma-neighbor degree / capped approx-betweenness (
              {nodeN}n/{edgeN}e). Full Gephi KG·Theology Context Map은 잔여.
            </>
          ) : (
            <>
              <strong className="lr-ask-empty-map-g3">lemma live = HOLD</strong>
              (실 KG·betweenness 아님
              {layer ? "" : " · layer loading"}).
            </>
          )}
        </p>

        {real ? (
          <div
            className="lr-ask-empty-map-real-pin"
            data-lr-ask-lemma-real-pin="1"
            aria-label="REAL lemma betweenness layer v0 summary"
          >
            <p className="lr-ask-empty-map-real-pin-title">
              REAL data layer v0 · degree_proxy + approx_betweenness
            </p>
            <ul className="lr-ask-empty-map-real-stats">
              <li>
                subgraph <strong>{nodeN}</strong>n / <strong>{edgeN}</strong>e
              </li>
              <li>
                metric <strong>{layer?.metric_primary}</strong>
                {layer?.metric_secondary ? ` · ${layer.metric_secondary}` : ""}
              </li>
              {topHub ? (
                <li>
                  top hub <strong>{topHub.id}</strong> deg={topHub.degree}
                  {topHub.approx_betweenness != null
                    ? ` · β≈${Number(topHub.approx_betweenness).toFixed(3)}`
                    : ""}
                </li>
              ) : null}
            </ul>
            {spineLabels.length > 0 ? (
              <p className="lr-ask-empty-map-real-spine" data-lr-ask-lemma-pack-spine="1">
                pack spine: {spineLabels.join(" · ")}
              </p>
            ) : null}
            {bridgeLabels.length > 0 ? (
              <p className="lr-ask-empty-map-real-bridges" data-lr-ask-lemma-bridge-hubs="1">
                bridge hubs: {bridgeLabels.join(" · ")}
              </p>
            ) : null}
          </div>
        ) : null}

        <ul className="lr-ask-empty-map-trust lr-ask-empty-map-trust--secondary" aria-label="보조 신뢰 핀">
          <li data-pin="citation">
            <span className="lr-ask-empty-map-pin-label">Citation</span>
            <span className="lr-ask-empty-map-pin-state">잠금 대기</span>
          </li>
          <li data-pin="hypo">
            <span className="lr-ask-empty-map-pin-label">[HYPO]</span>
            <span className="lr-ask-empty-map-pin-state">advisory</span>
          </li>
          <li data-pin={real ? "real" : "lemma"}>
            <span className="lr-ask-empty-map-pin-label">lemma layer</span>
            <span className="lr-ask-empty-map-pin-state">{real ? "REAL v0" : "HOLD"}</span>
          </li>
        </ul>

        <ul className="lr-ask-empty-map-edge-legend" aria-label="연결 유형 미리보기">
          <li>
            <span className="lr-ask-empty-map-swatch lr-ask-empty-map-swatch--path" aria-hidden />
            경로
          </li>
          <li>
            <span className="lr-ask-empty-map-swatch lr-ask-empty-map-swatch--cite" aria-hidden />
            인용
          </li>
          <li>
            <span className="lr-ask-empty-map-swatch lr-ask-empty-map-swatch--related" aria-hidden />
            연결
          </li>
          <li data-residual={real ? "lemma-real" : "lemma"}>
            <span
              className={`lr-ask-empty-map-swatch ${real ? "lr-ask-empty-map-swatch--lemma-real" : "lr-ask-empty-map-swatch--lemma"}`}
              aria-hidden
            />
            {real ? "lemma REAL v0" : "lemma HOLD"}
          </li>
        </ul>
      </details>
    </div>
  );
}
