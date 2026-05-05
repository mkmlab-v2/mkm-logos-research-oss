/**
 * @MKM12-METADATA
 * Type: UI
 * Vector: {S:0.7, L:0.7, K:0.8, M:0.3}
 * Balance: 88
 * Purpose: Developer MVP page for public NON_GATING graph insights exploration.
 * Keywords: Next.js, public graph, pagination, developer
 */
"use client";

import { useCallback, useEffect, useState } from "react";

type ConfidenceBand = "A" | "B" | "C";

type NodeRow = {
  node_id_public: string;
  anchor_ref: string;
  theme_tag: string;
  confidence_band: ConfidenceBand;
};

type EdgeRow = {
  source_node_id_public: string;
  target_node_id_public: string;
  edge_type: "semantic" | "causal_hint" | "contrast" | "temporal" | "contextual";
  weight_bucket: "low" | "mid" | "high";
};

type InsightRow = {
  insight_id: string;
  anchor_ref: string;
  theme_tag: string;
  insight_summary: string;
  confidence_band: ConfidenceBand;
};

type PublicGraphResponse = {
  schema: "public_graph_response_v1";
  version: string;
  policy_label: "NON_GATING";
  research_only: true;
  no_trading_advice: true;
  as_of_date: string;
  pagination: {
    limit: number;
    next_cursor: string | null;
  };
  nodes: NodeRow[];
  edges: EdgeRow[];
  insights: InsightRow[];
};

const DEFAULT_ANCHOR = "Gen.1.1";

export default function DeveloperGraphInsightsPage() {
  const [anchor, setAnchor] = useState(DEFAULT_ANCHOR);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [rows, setRows] = useState<PublicGraphResponse | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [accumulatedInsights, setAccumulatedInsights] = useState<InsightRow[]>([]);

  const fetchPage = useCallback(
    async (cursor: string | null, reset: boolean) => {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams({ anchor, limit: "5" });
        if (cursor) params.set("cursor", cursor);
        const res = await fetch(`/api/public/graph/insights?${params.toString()}`, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as PublicGraphResponse;
        setRows(data);
        setNextCursor(data.pagination.next_cursor);
        setAccumulatedInsights((prev) => (reset ? data.insights : [...prev, ...data.insights]));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    [anchor]
  );

  useEffect(() => {
    fetchPage(null, true);
  }, [fetchPage]);

  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "2rem 1rem 4rem" }}>
      <h1 style={{ marginBottom: 8 }}>Developer · Public Graph Insights (MVP)</h1>
      <p style={{ marginTop: 0, marginBottom: 16, opacity: 0.8 }}>
        NON_GATING 공개 탐색 전용 뷰입니다. 실전 트리거/투자 자문으로 사용하지 않습니다.
      </p>

      <section className="card" style={{ padding: "1rem", marginBottom: "1rem" }}>
        <label htmlFor="anchor-input" style={{ display: "block", marginBottom: 8, fontWeight: 600 }}>
          Anchor Ref
        </label>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <input
            id="anchor-input"
            value={anchor}
            onChange={(e) => setAnchor(e.target.value)}
            placeholder="Gen.1.1"
            style={{ minWidth: 240, padding: "0.5rem" }}
          />
          <button className="btn btn-primary" onClick={() => fetchPage(null, true)} disabled={loading}>
            {loading ? "Loading..." : "Search"}
          </button>
        </div>
      </section>

      {error ? (
        <section className="card" style={{ padding: "1rem", borderColor: "#ef4444" }}>
          <strong>오류:</strong> {error}
        </section>
      ) : null}

      {rows ? (
        <>
          <section className="card" style={{ padding: "1rem", marginBottom: "1rem" }}>
            <h2 style={{ marginTop: 0, marginBottom: 8 }}>Policy</h2>
            <p style={{ margin: 0 }}>
              <strong>{rows.policy_label}</strong> · research_only={String(rows.research_only)} ·
              no_trading_advice={String(rows.no_trading_advice)} · as_of={rows.as_of_date}
            </p>
          </section>

          <section className="card" style={{ padding: "1rem", marginBottom: "1rem" }}>
            <h2 style={{ marginTop: 0 }}>Insights ({accumulatedInsights.length})</h2>
            {accumulatedInsights.length === 0 ? <p>결과가 없습니다.</p> : null}
            <div style={{ display: "grid", gap: 10 }}>
              {accumulatedInsights.map((item) => (
                <article key={item.insight_id} style={{ border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8, padding: "0.75rem" }}>
                  <p style={{ margin: "0 0 6px 0", fontSize: 12, opacity: 0.8 }}>
                    {item.anchor_ref} · {item.theme_tag} · {item.confidence_band}
                  </p>
                  <p style={{ margin: 0 }}>{item.insight_summary}</p>
                </article>
              ))}
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
              <button className="btn btn-ghost" onClick={() => fetchPage(null, true)} disabled={loading}>
                Reset
              </button>
              <button className="btn btn-primary" onClick={() => fetchPage(nextCursor, false)} disabled={loading || !nextCursor}>
                {nextCursor ? "Load more" : "No more"}
              </button>
            </div>
          </section>

          <section className="card" style={{ padding: "1rem" }}>
            <h2 style={{ marginTop: 0 }}>Graph Snapshot</h2>
            <p style={{ marginTop: 0, opacity: 0.8 }}>
              nodes={rows.nodes.length} · edges={rows.edges.length} · next_cursor={rows.pagination.next_cursor ?? "null"}
            </p>
          </section>
        </>
      ) : null}
    </main>
  );
}
