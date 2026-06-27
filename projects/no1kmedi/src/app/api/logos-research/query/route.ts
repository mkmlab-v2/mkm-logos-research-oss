import { NextRequest, NextResponse } from "next/server";



import { hasLogosProAccess, resolveLogosAccess } from "@/lib/logosResearchAccessV1";
import {
  applyQuotaCookie,
  isEmbedDemoPreset,
  LOGOS_FREE_DAILY_QUOTA,
  quotaRemaining,
  readQuotaState,
} from "@/lib/logosResearchQuotaV1";

import {

  buildStudioQueryWithGraphrag,

  loadLogosStudioEmbeddingIndex,

  loadLogosStudioLexicalIndex,

  loadLogosStudioPresets,

  resolvePresetIdAsync,

} from "@/lib/logosResearchStudioV1";



type QueryBody = {
  preset_id?: string;
  query?: string;
  /** Hero iframe demo=1 — skips daily cookie quota (allowlisted presets only). */
  embed_demo?: boolean;
  /** B-track PoC — widens path depth divisor for ECS re-query hint. */
  ecs_expand_poc?: boolean;
};



export async function POST(request: NextRequest) {

  try {

    const body = (await request.json()) as QueryBody;
    const current = readQuotaState(request);
    const access = await resolveLogosAccess(request, "logos.query.read");
    const pro = hasLogosProAccess(access);
    const embedDemo = body.embed_demo === true;

    const presetsDoc = await loadLogosStudioPresets();
    const lexicalIndex = await loadLogosStudioLexicalIndex();
    const embeddingIndex = await loadLogosStudioEmbeddingIndex();
    const resolved = await resolvePresetIdAsync(
      presetsDoc.presets,
      {
        preset_id: body.preset_id,
        query: body.query,
      },
      lexicalIndex,
      embeddingIndex,
    );

    const embedDemoOk =
      embedDemo && resolved.preset_id != null && isEmbedDemoPreset(resolved.preset_id);

    if (!pro && !embedDemoOk && current.n >= LOGOS_FREE_DAILY_QUOTA) {

      const response = NextResponse.json(

        {

          ok: false,

          error: "quota_exceeded",

          free_daily_quota: LOGOS_FREE_DAILY_QUOTA,

          remaining: 0,

          upgrade_hint: "Pro beta API key or institution pilot — use lead form.",

        },

        { status: 429 },

      );

      applyQuotaCookie(response, current);

      return response;
    }

    const queryText = (body.query || "").trim();
    const ecsExpandPoc = body.ecs_expand_poc === true;
    const payload = await buildStudioQueryWithGraphrag(resolved.preset_id, queryText, {
      ecsExpandPoc,
    });



    if (!payload) {

      return NextResponse.json(

        {

          ok: false,

          error: resolved.preset_id ? "preset_missing" : "preset_not_matched",

          hint: "Rephrase the question or pick a preset seed.",

          remaining: quotaRemaining(current, pro),

        },

        { status: resolved.preset_id ? 404 : 400 },

      );

    }



    const nextState = pro || embedDemoOk ? current : { d: current.d, n: current.n + 1 };
    const response = NextResponse.json(
      {
        ok: true,
        api_contract: "logos_studio_v2_dynamic_rag_query_v1",
        api_contract_rev: "2026-06-25",
        match: resolved.match,
        remaining: quotaRemaining(nextState, pro || embedDemoOk),
        pro: pro || embedDemoOk,
        embed_demo: embedDemoOk,
        result: payload,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
    if (!pro && !embedDemoOk) applyQuotaCookie(response, nextState);

    return response;

  } catch (error: unknown) {

    const message = error instanceof Error ? error.message : "unknown_error";

    return NextResponse.json({ ok: false, error: message }, { status: 500 });

  }

}

