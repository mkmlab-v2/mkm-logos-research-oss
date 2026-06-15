"use client";

import { useMemo, useState } from "react";
import {
  appendLocalSttAuditRow,
  buildPasteSttAuditRow,
  type PersonadiarySttAuditLocalRowHypoV1,
} from "@/lib/personadiarySttAuditHypoV1";
import {
  classifyVoiceTranscript,
  formatVoiceSegmentsForDiary,
  VOICE_HUMAN_GATE_TEXT_KO,
  VOICE_PHASE_2B_DISCLAIMER_KO,
  type VoiceLaneClassification,
} from "@/lib/personadiaryVoiceLaneHypoV1";
import {
  localDateString,
  PERSONADIARY_LANE_LABELS,
  type PersonadiaryLane,
  type PersonadiaryMobileOpsV1,
} from "@/lib/personadiaryMobileOpsV1";

type Props = {
  ops: PersonadiaryMobileOpsV1;
  onPersist: (next: PersonadiaryMobileOpsV1) => Promise<PersonadiaryMobileOpsV1 | void>;
  saving?: boolean;
  onSaved?: (body: string) => void;
};

const RED_FLAG_COPY: Record<string, string> = {
  watch: "디지털 위생 주의 — 수면·스크롤 패턴 감지 · Pull 리마인더 권장",
  shield_hypo: "마음 레인 적색 신호 — 리소스 안내 · Human Gate 필수 (의료 triage 아님)",
  blocked: "금지 카피/임상 표현 차단 — 해당 구간은 저장에서 제외",
  none: "",
};

export function PersonadiaryVoiceDiaryHypoPanel({ ops, onPersist, saving, onSaved }: Props) {
  const [transcript, setTranscript] = useState("");
  const [classification, setClassification] = useState<VoiceLaneClassification | null>(null);
  const [sttAuditRow, setSttAuditRow] = useState<PersonadiarySttAuditLocalRowHypoV1 | null>(null);
  const [humanGate, setHumanGate] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const canClassify = transcript.trim().length > 0;
  const canSave = useMemo(() => {
    if (!classification || saving) return false;
    const hasApproved = classification.segments.some((s) => !s.blocked);
    if (!hasApproved) return false;
    if (classification.human_gate_required && !humanGate) return false;
    return true;
  }, [classification, humanGate, saving]);

  function runClassify() {
    setSaveError(null);
    setHumanGate(false);
    const sttEventId = crypto.randomUUID();
    const audit = buildPasteSttAuditRow(transcript, sttEventId);
    const result = classifyVoiceTranscript(transcript, {
      activeLaneHint: ops.active_lane,
      sttEventId,
    });
    setSttAuditRow(audit);
    setClassification(result);
  }

  async function saveVoiceDiary() {
    if (!classification || !sttAuditRow) return;
    const body = formatVoiceSegmentsForDiary(classification.segments, PERSONADIARY_LANE_LABELS);
    if (!body) {
      setSaveError("저장할 구간이 없습니다 (차단된 전사만 포함).");
      return;
    }
    if (classification.human_gate_required && !humanGate) {
      setSaveError("Human Gate 확인이 필요합니다.");
      return;
    }

    const entry = {
      date_local: localDateString(),
      body,
      lane: ops.active_lane,
      synced: false as const,
      voice_meta_hypo_v1: {
        hypothesis_tier: "B" as const,
        stt_event_id: sttAuditRow.event_id,
        segments: classification.segments.filter((s) => !s.blocked).length,
        human_gate_approved: humanGate || !classification.human_gate_required,
        mind_red_flag_tier: classification.mind_red_flag_tier,
        stt_route: sttAuditRow.route,
      },
    };
    const filtered = ops.diary_entries_local.filter((e) => e.date_local !== entry.date_local);
    await onPersist({
      ...ops,
      stt_audit_local_hypo_v1: appendLocalSttAuditRow(ops.stt_audit_local_hypo_v1, sttAuditRow),
      diary_entries_local: [...filtered, entry],
      checkpoints: [
        ...ops.checkpoints,
        { ts_utc: new Date().toISOString(), one_line: body.slice(0, 280) },
      ].slice(-64),
    });
    setTranscript("");
    setClassification(null);
    setSttAuditRow(null);
    setHumanGate(false);
    setSaveError(null);
    onSaved?.(body);
  }

  return (
    <section className="pd-ops-block pd-ops-voice-hypo" aria-labelledby="pd-voice-title">
      <p className="pd-ops-voice-hypo-marker" hidden>
        pd-ops-voice-hypo · Human Gate · Phase 2b · 말로 적기 stub
      </p>
      <div className="pd-premium-section-inner pd-glass pd-ops-card">
        <h2 id="pd-voice-title">
          말로 적기 <span className="pd-ops-hypo-tag">[HYPO · Phase 2b]</span>
        </h2>
        <p className="pd-ops-muted">{VOICE_PHASE_2B_DISCLAIMER_KO}</p>
        <textarea
          className="pd-ops-textarea"
          rows={4}
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="전사 붙여넣기 — 예: 오늘 회의가 많고 저녁에 산책하려고 해요"
          maxLength={4000}
          aria-label="음성 전사 붙여넣기"
        />
        <div className="pd-ops-row">
          <button
            type="button"
            className="btn btn-ghost"
            disabled={!canClassify || saving}
            onClick={runClassify}
          >
            4레인 분류
          </button>
        </div>

        {classification && (
          <div className="pd-ops-voice-preview" aria-live="polite">
            {classification.mind_red_flag_tier !== "none" && (
              <p className="pd-ops-hint pd-ops-voice-redflag">
                {RED_FLAG_COPY[classification.mind_red_flag_tier]}
              </p>
            )}
            <ul className="pd-ops-list pd-ops-voice-segments">
              {classification.segments.map((seg, idx) => (
                <li key={`${seg.lane}-${idx}`} className={seg.blocked ? "pd-ops-voice-blocked" : undefined}>
                  <span className="pd-ops-lane-chip">
                    {PERSONADIARY_LANE_LABELS[seg.lane as PersonadiaryLane]}
                  </span>
                  <span>
                    {seg.text}
                    {seg.blocked && <span className="pd-ops-hypo-tag"> [차단]</span>}
                    {seg.needs_review && !seg.blocked && (
                      <span className="pd-ops-hypo-tag"> [검토]</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
            {classification.human_gate_required && (
              <label className="pd-ops-check pd-ops-voice-gate">
                <input
                  type="checkbox"
                  checked={humanGate}
                  onChange={(e) => setHumanGate(e.target.checked)}
                />
                <span>{VOICE_HUMAN_GATE_TEXT_KO}</span>
              </label>
            )}
            <div className="pd-ops-row">
              <button
                type="button"
                className="btn btn-primary"
                disabled={!canSave}
                onClick={() => void saveVoiceDiary()}
              >
                일기에 저장
              </button>
            </div>
          </div>
        )}
        {saveError && <p className="pd-ops-error">{saveError}</p>}
      </div>
    </section>
  );
}
