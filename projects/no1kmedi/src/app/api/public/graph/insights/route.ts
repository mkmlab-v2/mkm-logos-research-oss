/**
 * @MKM12-METADATA
 * Type: Engine
 * Vector: {S:0.8, L:0.7, K:0.7, M:0.3}
 * Balance: 88
 * Purpose: Public NON_GATING graph insights endpoint for a-codeai.com.
 * Keywords: Next.js, API, public graph, NON_GATING
 */
import { NextRequest, NextResponse } from "next/server";
import path from "node:path";
import { promises as fs } from "node:fs";

type ConfidenceBand = "A" | "B" | "C";

type PublicNode = {
  node_id_public: string;
  anchor_ref: string;
  theme_tag: string;
  confidence_band: ConfidenceBand;
};

type PublicEdge = {
  source_node_id_public: string;
  target_node_id_public: string;
  edge_type: "semantic" | "causal_hint" | "contrast" | "temporal" | "contextual";
  weight_bucket: "low" | "mid" | "high";
};

type PublicInsight = {
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
  nodes: PublicNode[];
  edges: PublicEdge[];
  insights: PublicInsight[];
};

const MAX_LIMIT = 100;
const DEFAULT_LIMIT = 20;

async function resolveWorkspaceRoot(): Promise<string | null> {
  const fromEnv = process.env.MKM_WORKSPACE_ROOT?.trim();
  const candidates: string[] = [];
  if (fromEnv) candidates.push(path.resolve(fromEnv));

  const cwd = process.cwd();
  candidates.push(
    cwd,
    path.resolve(cwd, ".."),
    path.resolve(cwd, "..", ".."),
    path.resolve(cwd, "..", "..", ".."),
    path.resolve(cwd, "..", "..", "..", ".."),
    path.resolve(cwd, "..", "..", "..", "..", "..")
  );

  for (const root of candidates) {
    const probe = path.join(root, "docs", "final", "artifacts", "schemas", "public_graph_response_v1.example.json");
    try {
      await fs.access(probe);
      return root;
    } catch {
      // try next
    }
  }
  return null;
}

function parseLimit(raw: string | null): number {
  const n = Number.parseInt(raw ?? "", 10);
  if (Number.isNaN(n)) return DEFAULT_LIMIT;
  return Math.min(Math.max(n, 1), MAX_LIMIT);
}

function decodeCursor(raw: string | null): number {
  if (!raw) return 0;
  try {
    const decoded = Buffer.from(raw, "base64").toString("utf-8");
    const n = Number.parseInt(decoded, 10);
    if (Number.isNaN(n) || n < 0) return 0;
    return n;
  } catch {
    return 0;
  }
}

function encodeCursor(offset: number): string {
  return Buffer.from(String(offset), "utf-8").toString("base64");
}

export async function GET(req: NextRequest) {
  try {
    const root = await resolveWorkspaceRoot();
    if (!root) {
      return NextResponse.json(
        { success: false, error: "workspace_root_not_found", hint: "Set MKM_WORKSPACE_ROOT to monorepo root." },
        { status: 503 }
      );
    }

    const examplePath = path.join(
      root,
      "docs",
      "final",
      "artifacts",
      "schemas",
      "public_graph_response_v1.example.json"
    );
    const raw = await fs.readFile(examplePath, "utf-8");
    const doc = JSON.parse(raw) as PublicGraphResponse;

    const anchor = req.nextUrl.searchParams.get("anchor")?.trim() || "";
    const theme = req.nextUrl.searchParams.get("theme")?.trim() || "";
    const confidence = req.nextUrl.searchParams.get("confidence_band")?.trim() as ConfidenceBand | "";
    const limit = parseLimit(req.nextUrl.searchParams.get("limit"));
    const offset = decodeCursor(req.nextUrl.searchParams.get("cursor"));

    const allInsights = doc.insights
      .filter((x) => (anchor ? x.anchor_ref === anchor : true))
      .filter((x) => (theme ? x.theme_tag === theme : true))
      .filter((x) => (confidence ? x.confidence_band === confidence : true));
    const filteredInsights = allInsights.slice(offset, offset + limit);
    const nextOffset = offset + filteredInsights.length;
    const nextCursor = nextOffset < allInsights.length ? encodeCursor(nextOffset) : null;

    const linkedNodeIds = new Set<string>();
    for (const item of filteredInsights) {
      for (const node of doc.nodes) {
        if (node.anchor_ref === item.anchor_ref || node.theme_tag === item.theme_tag) {
          linkedNodeIds.add(node.node_id_public);
        }
      }
    }

    const filteredNodes = doc.nodes.filter((n) => (filteredInsights.length === 0 ? true : linkedNodeIds.has(n.node_id_public)));
    const filteredEdges = doc.edges.filter(
      (e) => filteredNodes.some((n) => n.node_id_public === e.source_node_id_public) && filteredNodes.some((n) => n.node_id_public === e.target_node_id_public)
    );

    const response: PublicGraphResponse = {
      ...doc,
      pagination: {
        limit,
        next_cursor: nextCursor
      },
      nodes: filteredNodes,
      edges: filteredEdges,
      insights: filteredInsights
    };

    return NextResponse.json(response, {
      status: 200,
      headers: {
        "Cache-Control": "public, max-age=60, s-maxage=60"
      }
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ success: false, error: "public_graph_insights_failed", message: message.slice(0, 300) }, { status: 500 });
  }
}
