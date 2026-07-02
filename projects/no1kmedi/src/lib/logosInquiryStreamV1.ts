/** Logos inquiry SSE stream v1 — P0-1b S4 chunk (mirrors scripts/core/logos_inquiry_stream_v1.py) */
import { createHash } from "node:crypto";

import type { LogosInquiryReportV1 } from "./logosInquiryReportV1";

export const STREAM_SCHEMA = "logos_inquiry_stream_v1";
export const DEFAULT_CHUNK_CHARS = 48;

export type StreamSnapshot = {
  S1: LogosInquiryReportV1["sections"]["S1"];
  S2: LogosInquiryReportV1["sections"]["S2"];
  S3: LogosInquiryReportV1["sections"]["S3"];
  S4_placeholder: {
    section_id: "S4_dynamic_synthesis";
    title_ko: string;
    body_ko: "";
    streaming: "active";
  };
  S5: {
    section_id: "S5_jema_integrity_signoff";
    title_ko: string;
    signoff_status: "provisional";
    chain_exit_code: number;
    artifact_path: string;
    sections_payload_sha256: null;
    freeze_verify_command: string;
    note_ko: string;
  };
  governance: LogosInquiryReportV1["governance"];
};

export type StreamEvent =
  | { schema: typeof STREAM_SCHEMA; event: "snapshot"; seq: 0; snapshot: StreamSnapshot }
  | {
      schema: typeof STREAM_SCHEMA;
      event: "s4_delta";
      seq: number;
      delta: { index: number; text: string };
    }
  | {
      schema: typeof STREAM_SCHEMA;
      event: "s4_done";
      seq: number;
      s4: { body_ko: string; bullets_ko: string[] };
    }
  | { schema: typeof STREAM_SCHEMA; event: "done"; seq: number; report: LogosInquiryReportV1 }
  | { schema: typeof STREAM_SCHEMA; event: "error"; seq: number; message: string };

function sortKeysDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeysDeep);
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    return Object.keys(obj)
      .sort()
      .reduce<Record<string, unknown>>((acc, key) => {
        acc[key] = sortKeysDeep(obj[key]);
        return acc;
      }, {});
  }
  return value;
}

export function chunkS4Body(text: string, chunkChars = DEFAULT_CHUNK_CHARS): string[] {
  const clean = (text || "").trim();
  if (!clean) return [];
  const parts = clean.split(/(?<=[.!?…])\s+/);
  const chunks: string[] = [];
  let buf = "";
  for (const part of parts) {
    const candidate = buf ? `${buf} ${part}`.trim() : part;
    if (candidate.length <= chunkChars) {
      buf = candidate;
      continue;
    }
    if (buf) chunks.push(buf);
    if (part.length <= chunkChars) {
      buf = part;
    } else {
      for (let i = 0; i < part.length; i += chunkChars) {
        chunks.push(part.slice(i, i + chunkChars));
      }
      buf = "";
    }
  }
  if (buf) chunks.push(buf);
  return chunks;
}

/** Immediate SSE placeholder while GraphRAG / Azure distill runs (no payload yet). */
export function buildPendingStreamSnapshot(query: string): StreamSnapshot {
  const q = (query || "").trim();
  return {
    S1: {
      section_id: "S1_citation_lock",
      title_ko: "Citation Lock (구절 인용)",
      verse_refs: [],
      citation_lock_anchors: [],
      security_note_ko: q
        ? `「${q.length > 80 ? `${q.slice(0, 78)}…` : q}」 — 경로·앵커 분석 중…`
        : "경로·앵커 분석 중…",
    },
    S2: {
      section_id: "S2_lexicon_hash",
      title_ko: "Lexicon Hash (원어 렉시콘)",
      lemma_edge_line_count: 0,
      min_line_count_floor: 0,
      floor_pass: true,
      freeze_manifest_pointer: "",
      manifest_sha256: "",
      lemma_edges_sha256: "",
      sidecar_corpus_sha256: "",
      path_token_preview: [],
      security_note_ko: "렉시콘·freeze pin 준비 중…",
    },
    S3: {
      section_id: "S3_context_divergence",
      title_ko: "Context Divergence (맥락/학파 분기)",
      groups: [],
      note_ko: "[NON_GATING] 학파·맥락 분기 분석 중…",
    },
    S4_placeholder: {
      section_id: "S4_dynamic_synthesis",
      title_ko: "Dynamic Synthesis (고차원 통찰)",
      body_ko: "",
      streaming: "active",
    },
    S5: {
      section_id: "S5_jema_integrity_signoff",
      title_ko: "JEMA Integrity Signoff (무결성 서명)",
      signoff_status: "provisional",
      chain_exit_code: 0,
      artifact_path: "docs/final/artifacts/logos_corpus_knowledge_freeze_manifest_v1.json",
      sections_payload_sha256: null,
      freeze_verify_command: "py scripts/check_logos_corpus_knowledge_freeze_manifest_v1.py",
      note_ko: "분석·합성 진행 중 — provisional.",
    },
    governance: {
      disclaimer_ko:
        "logos inquiry Standard — Track B [HYPO] · research_only · NON_GATING. 의료·진단·투자·실거래 지시가 아닙니다.",
      forbidden_claims: ["무환각 0%", "GPT 대체", "KRV/31k 원문 전체 공개", "투자·실매매 트리거"],
      quality_basis_ko: "eval·Brier·citation lock·freeze pin — 마케팅 환각률 주장 금지.",
    },
  };
}

export function buildStreamSnapshot(report: LogosInquiryReportV1): StreamSnapshot {
  const s5 = report.sections.S5;
  return {
    S1: report.sections.S1,
    S2: report.sections.S2,
    S3: report.sections.S3,
    S4_placeholder: {
      section_id: "S4_dynamic_synthesis",
      title_ko: report.sections.S4.title_ko,
      body_ko: "",
      streaming: "active",
    },
    S5: {
      section_id: "S5_jema_integrity_signoff",
      title_ko: s5.title_ko,
      signoff_status: "provisional",
      chain_exit_code: s5.chain_exit_code,
      artifact_path: s5.artifact_path,
      sections_payload_sha256: null,
      freeze_verify_command: s5.freeze_verify_command,
      note_ko: "S4 스트림 완료 후 final seal — 중간 provisional.",
    },
    governance: report.governance,
  };
}

export function* iterStreamEvents(
  report: LogosInquiryReportV1,
  chunkChars = DEFAULT_CHUNK_CHARS,
): Generator<StreamEvent> {
  let seq = 0;
  yield {
    schema: STREAM_SCHEMA,
    event: "snapshot",
    seq: 0 as const,
    snapshot: buildStreamSnapshot(report),
  };
  const body = report.sections.S4.body_ko || "";
  const bullets = report.sections.S4.bullets_ko || [];
  for (const [index, text] of chunkS4Body(body, chunkChars).entries()) {
    seq += 1;
    yield { schema: STREAM_SCHEMA, event: "s4_delta", seq, delta: { index, text } };
  }
  seq += 1;
  yield { schema: STREAM_SCHEMA, event: "s4_done", seq, s4: { body_ko: body, bullets_ko: bullets } };
  const finalReport: LogosInquiryReportV1 = {
    ...report,
    sections: {
      ...report.sections,
      S5: {
        ...report.sections.S5,
        signoff_status: "final",
      },
    },
  };
  seq += 1;
  yield { schema: STREAM_SCHEMA, event: "done", seq, report: finalReport };
}

export function formatSseEvent(event: StreamEvent): string {
  return `event: ${event.event}\ndata: ${JSON.stringify(event)}\n\n`;
}

export function sectionsPayloadSha256(
  s1: LogosInquiryReportV1["sections"]["S1"],
  s2: LogosInquiryReportV1["sections"]["S2"],
  s3: LogosInquiryReportV1["sections"]["S3"],
  s4: LogosInquiryReportV1["sections"]["S4"],
): string {
  const payload = sortKeysDeep({ S1: s1, S2: s2, S3: s3, S4: s4 });
  return createHash("sha256").update(JSON.stringify(payload), "utf8").digest("hex");
}
