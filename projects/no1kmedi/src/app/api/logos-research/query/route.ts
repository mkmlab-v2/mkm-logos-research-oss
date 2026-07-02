import { NextRequest, NextResponse } from "next/server";

import { domainLaneFromSurfaceHint } from "@/lib/surfaceContextNamespaceV1";

import { hasLogosProAccess, resolveLogosAccess } from "@/lib/logosResearchAccessV1";
import {
  applyInquiryS4QualityGate,
  buildLogosInquiryReport,
  evaluateLogosInquiryIntake,
  enrichLogosResearchQuery,
} from "@/lib/logosInquiryReportV1";
import {
  loadFreezeLexiconMeta,
  loadSasangRegimeHintBTrack,
} from "@/lib/logosInquiryFreezeMetaV1";
import { loadTextMvpHandoffSummary } from "@/lib/logosResearchHandoffServerV1";
import {
  buildLogosTextMvpReport,
  evaluateLogosTextMvpIntake,
} from "@/lib/logosResearchTextMvpV1";
import { formatSseEvent, iterStreamEvents, buildPendingStreamSnapshot, STREAM_SCHEMA } from "@/lib/logosInquiryStreamV1";
import {
  applyQuotaCookie,
  isEmbedDemoPreset,
  isLogosStudioQuotaDisabled,
  LOGOS_FREE_DAILY_QUOTA,
  quotaRemaining,
  readQuotaState,
} from "@/lib/logosResearchQuotaV1";
import { LOGOS_GRAPH_STUDIO_DEFAULT_PRESET } from "@/lib/logosGraphStudioEmbed";
import {
  buildStudioQueryWithGraphrag,
  loadLogosStudioEmbeddingIndex,
  loadLogosStudioLexicalIndex,
  loadLogosStudioPresets,
  resolveGen2EveCreationPresetOverride,
  resolvePresetIdAsync,
} from "@/lib/logosResearchStudioV1";
import { loadGolden200AnchorRegistry, resolveGoldenHubPresetId } from "@/lib/logosGolden200AnchorRegistryV1";
import { resolveVerseAnchorPresetId } from "@/lib/logosInquiryVerseThematicV1";

export const runtime = "nodejs";

type QueryBody = {
  preset_id?: string;
  query?: string;
  question?: string;
  output_format?: string;
  domain_lane?: string;
  domain_surface_hint?: string;
  intent_chip?: string;
  stream_s4?: boolean;
  embed_demo?: boolean;
  ecs_expand_poc?: boolean;
  azure_distill_mode?: "auto" | "force_on" | "force_off" | "on" | "off";
};

function isInquiryFormat(raw: string | undefined): boolean {
  return (raw || "").trim().toLowerCase() === "inquiry_report_v1";
}

function isTextMvpFormat(raw: string | undefined): boolean {
  return (raw || "").trim().toLowerCase() === "text_mvp_report_v1";
}

function isStructuredReportMode(raw: string | undefined): boolean {
  return isInquiryFormat(raw) || isTextMvpFormat(raw);
}

function isStreamS4(body: QueryBody): boolean {
  return body.stream_s4 === true;
}

function resolveAzureDistillMode(
  raw: QueryBody["azure_distill_mode"],
): "auto" | "force_on" | "force_off" {
  const mode = String(raw || "auto").trim().toLowerCase();
  if (mode === "force_on" || mode === "on") return "force_on";
  if (mode === "force_off" || mode === "off") return "force_off";
  return "auto";
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as QueryBody;
    const textMvpMode = isTextMvpFormat(body.output_format);
    const inquiryMode = isInquiryFormat(body.output_format);
    const structuredMode = isStructuredReportMode(body.output_format);
    const streamMode = inquiryMode && isStreamS4(body);
    const azureDistillMode = resolveAzureDistillMode(body.azure_distill_mode);
    const rawQuery = (body.query || body.question || "").trim();
    const { displayQuery, pipelineQuery } = enrichLogosResearchQuery(rawQuery);
    const headerHint = request.headers.get("X-JEMA-Domain-Surface-Hint")?.trim().toLowerCase() || "";
    const bodyHint = (body.domain_surface_hint || "").trim().toLowerCase();
    const surfaceHint = bodyHint || headerHint;
    const domainLane = surfaceHint
      ? domainLaneFromSurfaceHint(surfaceHint)
      : (body.domain_lane || "logos").trim().toLowerCase();
    const intentChip = (body.intent_chip || "reports").trim().toLowerCase();

    if (structuredMode) {
      const intake = textMvpMode
        ? evaluateLogosTextMvpIntake(rawQuery, domainLane, intentChip)
        : evaluateLogosInquiryIntake(rawQuery, domainLane, intentChip);
      if (intake.intake_gate !== "PASS") {
        return NextResponse.json(
          {
            ok: false,
            error: "intake_hold",
            api_contract: streamMode
              ? "logos_inquiry_stream_v1"
              : textMvpMode
                ? "logos_research_text_mvp_qa_v1"
                : "logos_inquiry_query_v1",
            output_format: textMvpMode ? "text_mvp_report_v1" : "inquiry_report_v1",
            intake,
            reverse_questions_ko: intake.reverse_questions_ko ?? [],
          },
          { status: 422 },
        );
      }
    }

    const current = readQuotaState(request);
    const access = await resolveLogosAccess(request, "logos.query.read");
    const pro = hasLogosProAccess(access);
    const embedDemo = body.embed_demo === true && !structuredMode;

    const presetsDoc = await loadLogosStudioPresets();
    const lexicalIndex = await loadLogosStudioLexicalIndex();
    const embeddingIndex = await loadLogosStudioEmbeddingIndex();
    let resolved = await resolvePresetIdAsync(
      presetsDoc.presets,
      { preset_id: body.preset_id, query: pipelineQuery },
      lexicalIndex,
      embeddingIndex,
    );

    const gen2Forced = resolveGen2EveCreationPresetOverride(
      pipelineQuery,
      presetsDoc.presets,
    );
    if (gen2Forced) {
      resolved = { preset_id: gen2Forced, match: "text" };
    } else {
      const verseForced = resolveVerseAnchorPresetId(presetsDoc.presets, pipelineQuery);
      if (verseForced) {
        resolved = { preset_id: verseForced, match: "text" };
      } else {
        const registry = await loadGolden200AnchorRegistry();
        const hubForced = registry
          ? resolveGoldenHubPresetId(presetsDoc.presets, pipelineQuery, registry)
          : null;
        if (hubForced) {
          resolved = { preset_id: hubForced, match: "text" };
        } else if (textMvpMode && !resolved.preset_id && pipelineQuery) {
          const fallbackId =
            presetsDoc.presets.find((p) => p.id === LOGOS_GRAPH_STUDIO_DEFAULT_PRESET)?.id ??
            presetsDoc.presets[0]?.id ??
            null;
          if (fallbackId) {
            resolved = { preset_id: fallbackId, match: "text" };
          }
        }
      }
    }

    const embedDemoOk =
      embedDemo && resolved.preset_id != null && isEmbedDemoPreset(resolved.preset_id);
    const quotaOff = isLogosStudioQuotaDisabled();

    if (!pro && !embedDemoOk && !quotaOff && current.n >= LOGOS_FREE_DAILY_QUOTA) {
      const response = NextResponse.json(
        {
          ok: false,
          error: "quota_exceeded",
          free_daily_quota: LOGOS_FREE_DAILY_QUOTA,
          remaining: 0,
          upgrade_hint: "GitHub Issues로 피드백 주세요 — 결제는 OSS 검증 후 연결 예정.",
        },
        { status: 429 },
      );
      applyQuotaCookie(response, current);
      return response;
    }

    const ecsExpandPoc = body.ecs_expand_poc === true;
    const nextState = pro || embedDemoOk || quotaOff ? current : { d: current.d, n: current.n + 1 };

    if (inquiryMode && streamMode) {
      const intake = evaluateLogosInquiryIntake(rawQuery, domainLane, intentChip);
      const chunkMs = Math.max(
        0,
        parseInt(process.env.LOGOS_INQUIRY_STREAM_CHUNK_MS || "0", 10) || 0,
      );
      const encoder = new TextEncoder();
      const presetId = resolved.preset_id;
      const stream = new ReadableStream({
        async start(controller) {
          const enqueue = (ev: Parameters<typeof formatSseEvent>[0]) => {
            controller.enqueue(encoder.encode(formatSseEvent(ev)));
          };
          try {
            enqueue({
              schema: STREAM_SCHEMA,
              event: "snapshot",
              seq: 0,
              snapshot: buildPendingStreamSnapshot(displayQuery),
            });

            const payload = await buildStudioQueryWithGraphrag(presetId, pipelineQuery, {
              ecsExpandPoc,
              azureDistillMode,
            });
            if (!payload) {
              enqueue({
                schema: STREAM_SCHEMA,
                event: "error",
                seq: 1,
                message: presetId ? "preset_missing" : "preset_not_matched",
              });
              controller.close();
              return;
            }

            const [freezeMeta, sasangHint] = await Promise.all([
              loadFreezeLexiconMeta(),
              loadSasangRegimeHintBTrack(),
            ]);
            const report = buildLogosInquiryReport(
              payload,
              displayQuery,
              intake,
              freezeMeta,
              0,
              sasangHint,
            );
            {
              const gate = applyInquiryS4QualityGate({
                body: report.sections.S4.body_ko,
                bullets: report.sections.S4.bullets_ko,
                verseRefs: report.sections.S1.verse_refs ?? [],
                query: displayQuery,
              });
              report.sections.S4.body_ko = gate.body;
              report.sections.S4.bullets_ko = report.sections.S4.bullets_ko.filter(
                (b) => !/lemma:gnosis:|shared_lemma=|Lemma\s*연결\s*이웃\s*구절|Path\s*envelope|orphan\s*veto|Gematria_Pin/i.test(b),
              );
              report.sections.S4.format_gate = {
                applied: true,
                missing_sections: gate.missing_sections,
                recomposed: gate.recomposed,
              };
            }

            for (const ev of iterStreamEvents(report)) {
              if (chunkMs > 0 && ev.event === "s4_delta") {
                await new Promise((resolve) => setTimeout(resolve, chunkMs));
              }
              enqueue(ev);
            }
            controller.close();
          } catch (error: unknown) {
            const message = error instanceof Error ? error.message : "unknown_error";
            enqueue({ schema: STREAM_SCHEMA, event: "error", seq: 99, message });
            controller.close();
          }
        },
      });
      const response = new Response(stream, {
        headers: {
          "Content-Type": "text/event-stream; charset=utf-8",
          "Cache-Control": "no-cache, no-transform",
          Connection: "keep-alive",
          "X-Logos-Api-Contract": "logos_inquiry_stream_v1",
          "X-Logos-Output-Format": "inquiry_report_v1",
          "X-Logos-Quota-Remaining": String(quotaRemaining(nextState, pro || quotaOff)),
        },
      });
      if (!pro && !quotaOff) {
        const wrapped = new NextResponse(response.body, response);
        applyQuotaCookie(wrapped, nextState);
        return wrapped;
      }
      return response;
    }

    const payload = await buildStudioQueryWithGraphrag(resolved.preset_id, pipelineQuery, {
      ecsExpandPoc,
      azureDistillMode,
    });

    if (!payload) {
      const topicHint =
        inquiryMode && !resolved.preset_id
          ? "질문 주제에 맞는 성경 권·장을 포함해 구체화해 주세요. (예: 요한계시록 13장 666, 요한일서 적그리스도)"
          : structuredMode
            ? "질문을 구체화해 주세요."
            : "Rephrase the question or pick a preset seed.";
      return NextResponse.json(
        {
          ok: false,
          error: resolved.preset_id ? "preset_missing" : "preset_not_matched",
          hint: topicHint,
          remaining: quotaRemaining(current, pro || quotaOff),
        },
        { status: resolved.preset_id ? 404 : inquiryMode ? 422 : 400 },
      );
    }

    if (textMvpMode) {
      const intake = evaluateLogosTextMvpIntake(rawQuery, domainLane, intentChip);
      const handoff = await loadTextMvpHandoffSummary();
      const report = buildLogosTextMvpReport(payload, displayQuery, intake, handoff);
      const response = NextResponse.json(
        {
          ok: true,
          api_contract: "logos_research_text_mvp_qa_v1",
          api_contract_rev: "2026-06-30",
          output_format: "text_mvp_report_v1",
          tier: "text_mvp",
          match: resolved.match,
          remaining: quotaRemaining(nextState, pro || quotaOff),
          intake,
          handoff,
          report,
        },
        { headers: { "Cache-Control": "no-store", "X-Logos-Output-Format": "text_mvp_report_v1" } },
      );
      if (!pro && !quotaOff) applyQuotaCookie(response, nextState);
      return response;
    }

    if (inquiryMode) {
      const intake = evaluateLogosInquiryIntake(rawQuery, domainLane, intentChip);
      const [freezeMeta, sasangHint] = await Promise.all([
        loadFreezeLexiconMeta(),
        loadSasangRegimeHintBTrack(),
      ]);
      const report = buildLogosInquiryReport(
        payload,
        displayQuery,
        intake,
        freezeMeta,
        0,
        sasangHint,
      );
      {
        const gate = applyInquiryS4QualityGate({
          body: report.sections.S4.body_ko,
          bullets: report.sections.S4.bullets_ko,
          verseRefs: report.sections.S1.verse_refs ?? [],
          query: displayQuery,
        });
        report.sections.S4.body_ko = gate.body;
        report.sections.S4.bullets_ko = report.sections.S4.bullets_ko.filter(
          (b) => !/lemma:gnosis:|shared_lemma=|Lemma\s*연결\s*이웃\s*구절|Path\s*envelope|orphan\s*veto|Gematria_Pin/i.test(b),
        );
        report.sections.S4.format_gate = {
          applied: true,
          missing_sections: gate.missing_sections,
          recomposed: gate.recomposed,
        };
      }

      const response = NextResponse.json(
        {
          ok: true,
          api_contract: "logos_inquiry_query_v1",
          api_contract_rev: "2026-06-30",
          output_format: "inquiry_report_v1",
          tier: "standard",
          match: resolved.match,
          remaining: quotaRemaining(nextState, pro || quotaOff),
          intake,
          report,
        },
        { headers: { "Cache-Control": "no-store" } },
      );
      if (!pro && !quotaOff) applyQuotaCookie(response, nextState);
      return response;
    }

    const response = NextResponse.json(
      {
        ok: true,
        api_contract: "logos_studio_v2_dynamic_rag_query_v1",
        api_contract_rev: "2026-06-25",
        output_format: "studio_v1",
        match: resolved.match,
        preset_guard: resolved.preset_guard ?? null,
        remaining: quotaRemaining(nextState, pro || embedDemoOk || quotaOff),
        pro: pro || embedDemoOk || quotaOff,
        quota_disabled: quotaOff,
        embed_demo: embedDemoOk,
        result: payload,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
    if (!pro && !embedDemoOk && !quotaOff) applyQuotaCookie(response, nextState);
    return response;
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
