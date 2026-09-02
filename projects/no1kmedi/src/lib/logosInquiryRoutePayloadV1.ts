/**
 * Inquiry-route payload resolver — wires offline-proven topical bootstrap + softmatch
 * before heavy GraphRAG (friend-battery DEV repair · F1/F2 fast path).
 */
import { evaluateLogosAskConfidenceGateV1 } from "./logosAskConfidenceGateV1";
import {
  buildTopicalFreeformBootstrap,
  type TopicalFreeformBootstrap,
} from "./logosFreeformTopicalInquiryV1";
import { applyInquiryVerseThematicLayer } from "./logosInquiryVerseThematicV1";
import { detectSchoolComparisonIntent } from "./logosInquiryTopicDetectV1";
import {
  buildStudioQueryWithGraphrag,
  type StudioQueryPayload,
} from "./logosResearchStudioV1";
import {
  logosStudioConflictRetrievalEnabled,
  retrieveLogosStudioConflictContext,
} from "./logosStudioConflictBridgeV1";

export function studioPayloadFromTopicalBootstrap(
  query: string,
  boot: TopicalFreeformBootstrap,
): StudioQueryPayload {
  const q = query.trim();
  const gate = evaluateLogosAskConfidenceGateV1(q);
  return {
    schema: "logos_research_studio_query_v1",
    research_only: true,
    send_gate: "HOLD",
    non_gating: true,
    preset_id: boot.preset_id,
    query_mode: boot.query_mode,
    query: q,
    answer: boot.answer,
    path: {
      note_ko: boot.one_liner_ko ?? "",
      steps: [],
      verse_refs: boot.verse_refs ?? [],
      node_ids: [],
      path_id: null,
      bridges_matched: null,
      reasoning_path_v1: null,
    },
    highlight_node_ids: [],
    subgraph: { graph_slice_url: "", highlight_count: 0 },
    disclaimer: null,
    insight_card: {
      preset_id: boot.preset_id,
      slot: "topical_bootstrap",
      slot_label_ko: "주제 부트스트랩",
      one_liner_ko: boot.one_liner_ko,
      verse_anchors: boot.verse_refs?.slice(0, 12),
      gap_ko: boot.gap_ko,
      governance: boot.governance,
    },
    ask_confidence: {
      route_band: gate.route_band,
      reasons: gate.reasons ?? [],
      hub_id: gate.hub_id ?? null,
    },
    honest_control: {
      citation_strength: boot.citation_strength,
      banner_ko: boot.honest_control_banner_ko,
    },
    citation_strength: boot.citation_strength,
  } as StudioQueryPayload;
}

async function attachConflictIfNeeded(
  payload: StudioQueryPayload,
  query: string,
): Promise<StudioQueryPayload> {
  if (!logosStudioConflictRetrievalEnabled() || !detectSchoolComparisonIntent(query)) {
    return payload;
  }
  const conflict = await retrieveLogosStudioConflictContext(query, payload.preset_id);
  if (conflict.ok && conflict.group_count > 0) {
    return { ...payload, conflict_context: conflict };
  }
  return payload;
}

/** Bootstrap-first inquiry payload — skips GraphRAG when topical bootstrap exists. */
export async function resolveInquiryStudioPayload(
  presetId: string | null,
  query: string,
  opts?: { ecsExpandPoc?: boolean; azureDistillMode?: "auto" | "force_on" | "force_off" },
): Promise<StudioQueryPayload | null> {
  const q = query.trim();
  const boot = buildTopicalFreeformBootstrap(q);
  if (boot) {
    let payload = applyInquiryVerseThematicLayer(
      studioPayloadFromTopicalBootstrap(q, boot),
      q,
    );
    payload = await attachConflictIfNeeded(payload, q);
    return payload;
  }
  return buildStudioQueryWithGraphrag(presetId, q, opts);
}
