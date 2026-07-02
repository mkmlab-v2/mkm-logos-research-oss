/** Text MVP report builder — mirrors scripts/core/logos_research_text_mvp_report_v1.py */
import type { StudioQueryPayload } from "./logosResearchStudioV1";
import type { ConflictContextResult } from "./logosStudioConflictBridgeV1";
import type { LemmaBridgeResult } from "./logosStudioLemmaBridgeV1";
import {
  enrichLogosResearchQuery,
  hasScriptureAnchor,
  logosResearchQuestionMinChars,
} from "./logosInquiryQueryEnrichV1";

export type LogosTextMvpIntakeSummary = {
  intake_gate: "PASS" | "HOLD";
  domain_lane?: string | null;
  intent_chip?: string | null;
  failed_checks?: string[];
  reverse_questions_ko?: string[];
};

export type LogosTextMvpHandoffSummary = {
  logos_surface: string;
  mkmlife_oracle_sphere_url: string;
  consumer_sku_note_ko: string;
  inference_queue_armed: boolean;
};

export type LogosTextMvpReportV1 = {
  schema: "logos_research_text_mvp_report_v1";
  version: string;
  generated_at_utc: string;
  research_only: boolean;
  non_gating: boolean;
  send_gate: string;
  query: string;
  preset_id?: string | null;
  intake: LogosTextMvpIntakeSummary;
  handoff: LogosTextMvpHandoffSummary;
  sections: {
    summary: { title_ko: string; body_ko: string; bullets_ko: string[] };
    citations: {
      title_ko: string;
      verse_refs: string[];
      citation_lock_anchors: string[];
      note_ko: string;
    };
    school_comparison: {
      title_ko: string;
      groups: Array<{
        conflict_group_id?: string;
        lexicon_base?: string;
        school_count?: number;
        schools: Array<{
          school_tier?: string;
          interpretation_ko?: string;
          verse_refs?: string[];
          citation_lock_anchors?: string[];
          traditions?: string[];
        }>;
      }>;
      note_ko: string;
    };
    word_network: {
      title_ko: string;
      path_steps: string[];
      node_ids: string[];
      lemma_neighbors: Array<{
        verse_ref?: string;
        shared_lemma_count?: number;
        lemma_ids?: string[];
      }>;
      note_ko: string;
    };
    gematria_insight: {
      title_ko: string;
      rows: Array<{
        kind: string;
        token: string;
        verse_ref?: string;
        note_ko: string;
      }>;
      note_ko: string;
    };
  };
  governance: {
    disclaimer_ko: string;
    forbidden_claims: string[];
    quality_basis_ko: string;
  };
  evidence_confidence?: StudioQueryPayload["evidence_confidence"] | null;
};

function stripHypo(text: string): string {
  return (text || "").replace(/^\[HYPO\]\s*/i, "").replace(/\[HYPO\]\s*/g, "").trim();
}

function splitBullets(text: string): string[] {
  const bullets: string[] = [];
  for (const line of (text || "").split("\n")) {
    const m = line.trim().match(/^[-*•]\s+(.+)$/);
    if (m) bullets.push(stripHypo(m[1]));
  }
  return bullets;
}

function extractCitationLockAnchors(payload: StudioQueryPayload): string[] {
  const anchors: string[] = [];
  const seen = new Set<string>();
  const conflict = payload.conflict_context as Extract<ConflictContextResult, { ok: true }> | null;
  if (conflict?.groups) {
    for (const group of conflict.groups) {
      for (const school of group.schools ?? []) {
        for (const anchor of school.citation_lock_anchors ?? []) {
          const t = String(anchor).trim();
          if (t && !seen.has(t)) {
            seen.add(t);
            anchors.push(t);
          }
        }
      }
    }
  }
  for (const ref of payload.path?.verse_refs ?? []) {
    const t = String(ref).trim();
    if (t && !seen.has(t)) {
      seen.add(t);
      anchors.push(t);
    }
  }
  return anchors;
}

function buildSchoolGroups(payload: StudioQueryPayload): LogosTextMvpReportV1["sections"]["school_comparison"]["groups"] {
  const conflict = payload.conflict_context as Extract<ConflictContextResult, { ok: true }> | null;
  if (!conflict?.groups?.length) return [];
  return conflict.groups.map((group) => ({
    conflict_group_id: group.conflict_group_id,
    lexicon_base: group.lexicon_base,
    school_count: group.school_count ?? group.schools?.length ?? 0,
    schools: (group.schools ?? []).map((school) => ({
      school_tier: school.school_tier,
      interpretation_ko: stripHypo(school.interpretation_ko ?? ""),
      verse_refs: school.verse_refs ?? [],
      citation_lock_anchors: school.citation_lock_anchors ?? [],
      traditions: school.traditions ?? [],
    })),
  }));
}

function buildLemmaNeighbors(payload: StudioQueryPayload): LogosTextMvpReportV1["sections"]["word_network"]["lemma_neighbors"] {
  const lemma = payload.lemma_bridge_meta as Extract<LemmaBridgeResult, { ok: true }> | null | undefined;
  if (!lemma?.ok || !lemma.neighbors?.length) return [];
  return lemma.neighbors.slice(0, 16).map((row) => ({
    verse_ref: row.verse_ref,
    shared_lemma_count: row.shared_lemma_count,
    lemma_ids: row.lemma_ids ?? [],
  }));
}

function buildGematriaRows(payload: StudioQueryPayload): LogosTextMvpReportV1["sections"]["gematria_insight"]["rows"] {
  const rows: LogosTextMvpReportV1["sections"]["gematria_insight"]["rows"] = [];
  const seen = new Set<string>();
  const tokens = [...(payload.path?.node_ids ?? []), ...(payload.path?.steps ?? [])];
  for (const raw of tokens) {
    const token = String(raw).trim();
    if (!token || seen.has(token)) continue;
    seen.add(token);
    if (/^lemma_/i.test(token)) {
      rows.push({
        kind: "lemma_anchor",
        token: token.replace(/^lemma_/i, ""),
        note_ko: "원어 lemma 앵커 — 게마트리아·Strong 연결은 연구 톤 관측.",
      });
    } else if (/^G?\d{3,5}$/i.test(token.replace(/^strongs:/i, ""))) {
      rows.push({
        kind: "strongs_ref",
        token,
        note_ko: "Strong 번호 참조 — 수치 해석은 [HYPO] 연구 보조.",
      });
    } else if (/gematria|gnosis/i.test(token)) {
      rows.push({ kind: "graph_node", token, note_ko: "그래프 노드 관측." });
    }
  }
  const lemma = payload.lemma_bridge_meta as Extract<LemmaBridgeResult, { ok: true }> | null | undefined;
  if (lemma?.ok) {
    for (const neighbor of lemma.neighbors ?? []) {
      for (const lemmaId of neighbor.lemma_ids ?? []) {
        const lid = String(lemmaId).trim();
        if (!lid || seen.has(lid)) continue;
        seen.add(lid);
        rows.push({
          kind: "shared_lemma",
          token: lid,
          verse_ref: neighbor.verse_ref,
          note_ko: "공유 lemma — 게마트리아·어휘 네트워크 연구 단서.",
        });
      }
    }
  }
  return rows.slice(0, 24);
}

export function buildLogosTextMvpReport(
  payload: StudioQueryPayload,
  query: string,
  intake: LogosTextMvpIntakeSummary,
  handoff: LogosTextMvpHandoffSummary,
): LogosTextMvpReportV1 {
  const answer = stripHypo(payload.answer ?? "");
  const verseRefs = (payload.path?.verse_refs ?? []).map((v) => String(v).trim()).filter(Boolean);
  const pathSteps = (payload.path?.steps ?? []).map((s) => String(s).trim()).filter(Boolean);
  const nodeIds = (payload.path?.node_ids ?? []).map((n) => String(n).trim()).filter(Boolean);
  const summaryBullets = splitBullets(payload.answer ?? "");
  if (payload.insight_card?.gap_ko) {
    summaryBullets.push(stripHypo(payload.insight_card.gap_ko));
  }

  return {
    schema: "logos_research_text_mvp_report_v1",
    version: "1.0.0",
    generated_at_utc: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    research_only: payload.research_only ?? true,
    non_gating: payload.non_gating ?? true,
    send_gate: payload.send_gate ?? "HOLD",
    query: query.trim(),
    preset_id: payload.preset_id,
    intake,
    handoff,
    sections: {
      summary: {
        title_ko: "연구 요약",
        body_ko: answer || "응답 본문을 생성하지 못했습니다.",
        bullets_ko: summaryBullets.slice(0, 8),
      },
      citations: {
        title_ko: "구절·인용 (citation lock)",
        verse_refs: verseRefs.slice(0, 24),
        citation_lock_anchors: extractCitationLockAnchors(payload).slice(0, 24),
        note_ko: "인용은 citation lock·canonical verse ref 기준 — 전문 KRV·31k 그래프 공개 주장 아님.",
      },
      school_comparison: {
        title_ko: "학파·해석 비교",
        groups: buildSchoolGroups(payload),
        note_ko: "[NON_GATING] 학파 비교는 연구·해설 보조 — 투자·실매매·Track A 트리거 아님.",
      },
      word_network: {
        title_ko: "단어·lemma 네트워크",
        path_steps: pathSteps.slice(0, 32),
        node_ids: nodeIds.slice(0, 32),
        lemma_neighbors: buildLemmaNeighbors(payload),
        note_ko: "그래픽·Studio 제외 — 경로·lemma 이웃만 텍스트로 제공.",
      },
      gematria_insight: {
        title_ko: "게마트리아·원어 통찰",
        rows: buildGematriaRows(payload),
        note_ko: "연구 톤 [HYPO] — 무환각·GPT 대체 주장 없음 · eval·Brier·citation lock 품질 기준.",
      },
    },
    governance: {
      disclaimer_ko:
        "성경 연구·일반 고민 Q&A — Track B [HYPO] · research_only · NON_GATING. 의료·진단·투자·실거래 지시가 아닙니다.",
      forbidden_claims: [
        "무환각 0%",
        "GPT 대체",
        "투자·실매매 트리거",
        "31k full graph GitHub 공개",
        "KRV 전문 공개",
      ],
      quality_basis_ko: "품질은 eval·Brier·citation lock으로만 — 마케팅 환각률 주장 금지.",
    },
    evidence_confidence: payload.evidence_confidence ?? null,
  };
}

export function evaluateLogosTextMvpIntake(
  question: string,
  domainLane = "logos",
  intentChip = "reports",
): LogosTextMvpIntakeSummary {
  const q = question.trim();
  const failures: string[] = [];
  const reverse: string[] = [];
  const minChars = logosResearchQuestionMinChars(q);

  if (q.length < minChars) {
    failures.push("question_too_short");
    reverse.push(
      hasScriptureAnchor(q)
        ? "성경 구절·권명을 포함해 조금 더 구체적으로 입력해 주세요."
        : "한 문장으로 구체적 질문을 입력해 주세요(최소 12자).",
    );
  }
  if (q.length < 24 && /뭐가 좋을까|알려줘|어떻게 생각해|전부 다|다 해줘/.test(q)) {
    failures.push("vague_only_question");
    reverse.push("구절·주제·상황 중 하나를 포함해 질문을 구체화해 주세요.");
  }
  if (/live\s*trad|실매매|매수해|매도해|start_live_trading|투자\s*해도|수익\s*보장/i.test(q)) {
    failures.push("forbidden_live_trading");
    reverse.push("실매매·투자 실행 지시는 지원하지 않습니다. 연구·관측 목적만 입력해 주세요.");
  }
  if (/진단해|처방해|약\s*추천|수술\s*해도|치료\s*해줘|diagnos|prescri/i.test(q)) {
    failures.push("forbidden_clinical_diagnosis");
    reverse.push("진단·처방 대체 요청은 지원하지 않습니다. 관측·체험 목적만 입력해 주세요.");
  }

  return {
    intake_gate: failures.length ? "HOLD" : "PASS",
    domain_lane: domainLane,
    intent_chip: intentChip,
    failed_checks: failures,
    reverse_questions_ko: reverse,
  };
}

export const DEFAULT_TEXT_MVP_HANDOFF: LogosTextMvpHandoffSummary = {
  logos_surface: "logos.jema-ai.com/logos-research/ask",
  mkmlife_oracle_sphere_url: "https://mkmlife.com/oracle-sphere",
  consumer_sku_note_ko: "초개인화 소비자 SKU는 mkmlife /oracle-sphere — 본 표면은 연구 워크스페이스.",
  inference_queue_armed: false,
};
