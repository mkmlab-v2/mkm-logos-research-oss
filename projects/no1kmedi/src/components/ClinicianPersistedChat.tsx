"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ClinicianChatThread, ClinicianChatTurn } from "@/lib/clinician-chat-types";
import { buildClinicianConsultPayload } from "@/lib/clinician-consult-payload-v1";
import { cdsSnapshotFromApi, formatCdsAssistantMessage } from "@/lib/clinician-chat-format";
import { streamTextClient } from "@/lib/consumer-chat-stream";
import { formatIntakePinInput, triageBadgeClass, triageLabel } from "@/lib/clinician-intake-utils";
import { ClinicianCdsFeedbackBar } from "@/components/ClinicianCdsFeedbackBar";

type AdvancedConsultResponse = {
  success: boolean;
  error?: string;
  draft?: {
    request_id: string;
    clinical_summary: string;
    profile_summary: { sasang_candidate: string; saju_reference: string };
    reasoning: { syndrome_hypothesis: string; care_direction: string; caution: string };
    non_medical_notice: string;
  };
  km_cds?: {
    envelope?: Record<string, unknown>;
    validation?: { ok: boolean; method: string; error?: string };
  };
};

type ClinicianPersistedChatProps = {
  thread: ClinicianChatThread;
  onCommit: (patch: Partial<ClinicianChatThread> & { id: string }) => void;
  canUseAdvancedConsult: boolean;
  onOpenPatientSettings: () => void;
  onOpenBundle: () => void;
};

export function ClinicianPersistedChat({
  thread,
  onCommit,
  canUseAdvancedConsult,
  onOpenPatientSettings,
  onOpenBundle,
}: ClinicianPersistedChatProps) {
  const [turns, setTurns] = useState<ClinicianChatTurn[]>(thread.turns);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [streamBuf, setStreamBuf] = useState<string | null>(null);
  const requestGen = useRef(0);

  useEffect(() => {
    setTurns(thread.turns);
    setStreamBuf(null);
    setError("");
    setMessage("");
  }, [thread.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const ctx = thread.context;
  const canSend = useMemo(
    () => message.trim().length > 1 && !busy && canUseAdvancedConsult,
    [message, busy, canUseAdvancedConsult],
  );

  const persist = useCallback(
    (patch: Partial<ClinicianChatThread> & { id: string }) => onCommit(patch),
    [onCommit],
  );

  const contextChips = useMemo(() => {
    const chips: string[] = [];
    if (ctx.birthInstantUtc.trim()) chips.push(`출생 ${ctx.birthInstantUtc.trim().slice(0, 10)}…`);
    if (ctx.ianaTz.trim()) chips.push(ctx.ianaTz.trim());
    if (ctx.loadedSurveyContext) chips.push(`PIN ${ctx.loadedSurveyContext.intakePin}`);
    if (ctx.chiefComplaint.trim()) chips.push(`주호소 설정됨`);
    return chips;
  }, [ctx]);

  const runConsult = useCallback(async () => {
    if (!canSend) return;
    const gen = ++requestGen.current;
    const userMessage = message.trim();
    const contextNext = {
      ...ctx,
      chiefComplaint: ctx.chiefComplaint.trim() || userMessage,
      onset: ctx.onset.trim() || "대화 입력",
      severity: ctx.severity.trim() || "미기재",
    };
    const requestId = `req_${Date.now()}`;
    const turnsWithUser: ClinicianChatTurn[] = [...turns, { role: "user", message: userMessage }];
    setMessage("");
    setBusy(true);
    setError("");
    setStreamBuf(null);
    setTurns(turnsWithUser);
    persist({
      id: thread.id,
      turns: turnsWithUser,
      context: contextNext,
    });

    try {
      const payload = buildClinicianConsultPayload(contextNext, requestId);
      const res = await fetch("/api/cdss/advanced-consult?validate_km_cds_envelope=1", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...payload,
          lens_mode: contextNext.lensMode,
          include_scripture: contextNext.includeScripture,
        }),
      });
      const json = (await res.json()) as AdvancedConsultResponse;
      if (gen !== requestGen.current) return;
      if (!res.ok || !json.success || !json.draft) {
        throw new Error(json.error || "consult_failed");
      }
      const full = formatCdsAssistantMessage(json.draft, json.km_cds);
      await streamTextClient(full, (partial) => {
        if (gen !== requestGen.current) return;
        setStreamBuf(partial);
      });
      if (gen !== requestGen.current) return;
      const turnsFinal: ClinicianChatTurn[] = [...turnsWithUser, { role: "assistant", message: full }];
      const lastCds = cdsSnapshotFromApi(requestId, json.draft, json.km_cds);
      setTurns(turnsFinal);
      setStreamBuf(null);
      persist({
        id: thread.id,
        turns: turnsFinal,
        context: contextNext,
        lastCds,
      });
    } catch {
      if (gen !== requestGen.current) return;
      setError("진료 보조 초안 생성에 실패했습니다. 「환자·설정」에서 출생·권한을 확인해 주세요.");
    } finally {
      if (gen === requestGen.current) {
        setBusy(false);
        setStreamBuf(null);
      }
    }
  }, [canSend, ctx, message, persist, thread.id, turns]);

  return (
    <section className="workspace-chat-root clinician-chat-root" aria-label="한의사 진료 보조 대화">
      <div className="chat-card chat-card--workspace chat-card--clinician">
        <div className="clinician-chat-toolbar">
          {contextChips.length ? (
            <div className="clinician-context-chips" aria-label="환자 맥락">
              {contextChips.map((c) => (
                <span key={c} className="clinician-context-chip">
                  {c}
                </span>
              ))}
            </div>
          ) : (
            <p className="workspace-muted clinician-chat-hint">출생·문진은 「환자·설정」에서 입력하세요.</p>
          )}
          <div className="clinician-chat-toolbar-actions">
            <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenPatientSettings}>
              환자·설정
            </button>
            {thread.lastCds?.validationOk ? (
              <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenBundle}>
                환자 번들
              </button>
            ) : null}
          </div>
        </div>

        {!canUseAdvancedConsult ? (
          <p className="consult-error">Pro 임상 보조 권한 확인 후 대화를 사용할 수 있습니다. 「환자·설정」에서 이메일을 확인하세요.</p>
        ) : null}

        {ctx.loadedSurveyContext ? (
          <p className="consult-source-chip clinician-pin-chip">
            {ctx.loadedSurveyContext.intakePin} / {ctx.loadedSurveyContext.patientName}{" "}
            <span className={triageBadgeClass(ctx.loadedSurveyContext.triageLevel)}>
              {triageLabel(ctx.loadedSurveyContext.triageLevel)}
            </span>
          </p>
        ) : null}

        <div className="chat-log" role="log" aria-live="polite">
          {turns.map((turn, idx) => (
            <p key={`${turn.role}-${idx}`} className={`chat-bubble chat-bubble-${turn.role}`}>
              <strong>{turn.role === "assistant" ? "보조" : "나"}</strong> {turn.message}
            </p>
          ))}
          {streamBuf !== null ? (
            <p className="chat-bubble chat-bubble-assistant chat-bubble-streaming">
              <strong>보조</strong> {streamBuf}
              <span className="chat-stream-caret" aria-hidden="true" />
            </p>
          ) : null}
          {busy && streamBuf === null ? (
            <p className="chat-bubble chat-bubble-assistant">
              <strong>보조</strong> 초안을 생성 중입니다…
            </p>
          ) : null}
        </div>

        <ClinicianCdsFeedbackBar
          requestId={thread.lastCds?.requestId}
          disabled={!canUseAdvancedConsult || busy}
        />

        <div className="chat-input-row clinician-chat-input-row">
          <textarea
            className="clinician-chat-textarea"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="주증상·추가 질문을 입력하세요. Enter로 전송, Shift+Enter 줄바꿈"
            rows={2}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void runConsult();
              }
            }}
          />
          <button className="btn btn-primary" type="button" onClick={() => void runConsult()} disabled={!canSend}>
            {busy ? "생성 중…" : "전송"}
          </button>
        </div>
        {error ? <p className="consult-error">{error}</p> : null}
      </div>
    </section>
  );
}
