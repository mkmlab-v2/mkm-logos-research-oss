/**
 * Read-only DSSBW canon cite lookup for clinician assist [교육·문화].
 */
import { NextRequest, NextResponse } from "next/server";

import { lookupKmCanonCiteChunks } from "@/lib/km-dssbw-canon-cite-bridge-v1";

export async function GET(request: NextRequest) {
  const q = (request.nextUrl.searchParams.get("q") || "").trim();
  if (q.length < 2) {
    return NextResponse.json({ success: false, error: "query_too_short" }, { status: 400 });
  }

  const limitRaw = request.nextUrl.searchParams.get("limit");
  const limit = limitRaw ? Number.parseInt(limitRaw, 10) : 3;
  const result = lookupKmCanonCiteChunks(q, { limit: Number.isFinite(limit) ? limit : 3 });

  if (!result.ok) {
    const status = result.method === "skipped" ? 503 : 500;
    return NextResponse.json(
      {
        success: false,
        error: result.error,
        track: "research_only",
        send_gate: "HOLD",
        guardrail: "encyclopedic_ref_only_not_diagnosis",
      },
      { status, headers: { "Cache-Control": "no-store" } },
    );
  }

  return NextResponse.json(
    {
      success: true,
      track: "research_only",
      send_gate: "HOLD",
      query: result.query,
      ranker: result.ranker,
      hit_count: result.hit_count,
      chunks: result.chunks,
      disclaimer_ko:
        "원전 인용은 교육·문화 맥락 참고용입니다. 진단·처방·체질 확정 트리거가 아닙니다.",
      philosophy_hypo_note_ko:
        "함억·두견 등 철학 서사는 [HYPO] 보조 맥락이며 phenotyping·자동 처방에 사용하지 않습니다.",
    },
    { status: 200, headers: { "Cache-Control": "no-store" } },
  );
}
