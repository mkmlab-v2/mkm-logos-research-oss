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
  onOpenPasteChart?: () => void;
};

export function ClinicianPersistedChat({
  thread,
  onCommit,
  canUseAdvancedConsult,
  onOpenPatientSettings,
  onOpenBundle,
  onOpenPasteChart,
}: ClinicianPersistedChatProps) {
  const [turns, setTurns] = useState<ClinicianChatTurn[]>(thread.turns);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [streamBuf, setStreamBuf] = useState<string | null>(null);
  const [auxOpen, setAuxOpen] = useState(false);
  const requestGen = useRef(0);
  const logRef = useRef<HTMLDivElement | null>(null);

  const starterPrompts = useMemo(
    () => ["두통·어지럼 주호소 정리", "소화불량·식후 팽만 상담 초안", "수면·피로 패턴 참고 요약"],
    [],
  );

  useEffect(() => {
    setTurns(thread.turns);
    setStreamBuf(null);
    setError("");
    setMessage("");
  }, [thread.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const el = logRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [turns, streamBuf, busy]);

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
    if (ctx.pasteChartFusion?.patientLabel) chips.push(`Paste Chart · ${ctx.pasteChartFusion.patientLabel}`);
    return chips;
  }, [ctx]);

  const pasteFusion = ctx.pasteChartFusion;

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
        <header className="clinician-chat-stage-head">
          <div className="clinician-chat-stage-context" aria-label="환자 맥락">
            {contextChips.length ? (
              contextChips.slice(0, 2).map((c) => (
                <span key={c} className="clinician-context-chip">
                  {c}
                </span>
              ))
            ) : (
              <span className="clinician-chat-stage-context-empty">환자 맥락 미설정</span>
            )}
          </div>
          <button
            type="button"
            className="clinician-chat-settings-btn"
            onClick={onOpenPatientSettings}
            aria-label="환자·설정"
            title="환자·설정"
          >
            ⚙
          </button>
        </header>

        {!canUseAdvancedConsult ? (
          <div className="clinician-access-gate" role="status">
            <p>
              Pro 임상 보조 권한 확인 후 CDSS 초안을 생성할 수 있습니다. 「환자·설정」에서 한의사 이메일을
              입력·확인하세요.
            </p>
            <button type="button" className="btn btn-primary btn-sm" onClick={onOpenPatientSettings}>
              환자·설정 열기
            </button>
          </div>
        ) : null}

        {pasteFusion ? (
          <div className="paste-chart-fusion-strip" role="status">
            <strong>Paste Chart 연동</strong>
            <span>
              {pasteFusion.patientLabel}
              {pasteFusion.adviceTitles?.length
                ? ` · ${pasteFusion.adviceTitles.slice(0, 4).join(" · ")}`
                : ""}
            </span>
            {pasteFusion.assessmentLine ? (
              <span className="paste-chart-fusion-assessment">{pasteFusion.assessmentLine}</span>
            ) : null}
          </div>
        ) : null}

        {ctx.loadedSurveyContext ? (
          <p className="consult-source-chip clinician-pin-chip">
            {ctx.loadedSurveyContext.intakePin} / {ctx.loadedSurveyContext.patientName}{" "}
            <span className={triageBadgeClass(ctx.loadedSurveyContext.triageLevel)}>
              {triageLabel(ctx.loadedSurveyContext.triageLevel)}
            </span>
          </p>
        ) : null}

        <div
          ref={logRef}
          className="chat-log clinician-chat-log"
          role="log"
          aria-live="polite"
          aria-busy={busy}
        >
          {turns.length === 0 && !busy && streamBuf === null ? (
            <div className="clinician-pilot-empty">
              <h2>진료 보조 대화</h2>
              <p>주증상을 입력하면 SOAP·CDSS 참고 초안을 정리합니다.</p>
              <div className="clinician-pilot-starters" aria-label="예시 질문">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="clinician-pilot-starter-btn"
                    onClick={() => setMessage(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
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
            <div className="chat-bubble chat-bubble-assistant" aria-label="초안 생성 중">
              <strong>보조</strong>
              <div className="clinician-pilot-skeleton" aria-hidden="true">
                <span className="clinician-pilot-skeleton-line" />
                <span className="clinician-pilot-skeleton-line" />
                <span className="clinician-pilot-skeleton-line" />
              </div>
            </div>
          ) : null}
        </div>

        <details
          className="clinician-aux-drawer"
          open={auxOpen}
          onToggle={(e) => setAuxOpen((e.target as HTMLDetailsElement).open)}
        >
          <summary>보조 작업</summary>
          <div className="clinician-aux-drawer-body">
            {pasteFusion && onOpenPasteChart ? (
              <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenPasteChart}>
                Paste Chart
              </button>
            ) : null}
            {thread.lastCds?.validationOk ? (
              <button type="button" className="btn btn-ghost btn-sm" onClick={onOpenBundle}>
                환자 번들
              </button>
            ) : (
              <span className="workspace-muted clinician-aux-hint">CDSS 초안 생성 후 번들을 열 수 있습니다.</span>
            )}
          </div>
        </details>

        <ClinicianCdsFeedbackBar
          requestId={thread.lastCds?.requestId}
          disabled={!canUseAdvancedConsult || busy}
        />

        <div className="chat-input-row clinician-chat-input-row">
          <textarea
            className="clinician-chat-textarea"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={
              canUseAdvancedConsult
                ? "주증상·추가 질문을 입력하세요. Enter로 전송, Shift+Enter 줄바꿈"
                : "질문을 미리 적어 두세요. 전송은 Pro 권한 확인 후 가능합니다."
            }
            rows={2}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void runConsult();
              }
            }}
          />
          <button
            className="btn btn-primary"
            type="button"
            onClick={() => void runConsult()}
            disabled={!canSend}
            title={!canUseAdvancedConsult ? "환자·설정에서 Pro 권한을 확인하세요" : undefined}
          >
            {busy ? "생성 중…" : canUseAdvancedConsult ? "전송" : "권한 필요"}
          </button>
        </div>
        {error ? <p className="consult-error">{error}</p> : null}
      </div>
    </section>
  );
}
