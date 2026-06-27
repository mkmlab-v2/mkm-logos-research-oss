"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  appendRitualDrawLog,
  applyGuideOverlay,
  buildMkmlifeHandoffUrl,
  fetchRitualLut,
  loadSessionDraw,
  persistSessionDraw,
  randomDrawToken,
  resolveLutCard,
  type RitualDrawResult,
  type RitualLutDoc,
} from "@/lib/personadiaryRitualDrawV1";
import {
  buildLatticeSession,
  fetchLatticeBloomSlice,
  LATTICE_BREATH_MS,
  LATTICE_CONVERGE_MS,
  latticePhaseDurationMs,
  persistLatticeSession,
  rankBloomHubs,
  shatterQuestionTokens,
  type BloomSliceDoc,
  type LatticePhase,
  type MatchedHub,
} from "@/lib/personadiaryLatticeConvergenceV1";
import { sanitizeMomentLine } from "@/lib/personadiaryMomentDisplay";
import { PersonadiaryLatticeOverlay } from "./PersonadiaryLatticeOverlay";
import { PersonadiaryMagicOrb } from "./PersonadiaryMagicOrb";
import { PersonadiaryReasoningTheatre } from "./PersonadiaryReasoningTheatre";
import {
  fetchMkmlifeReasoningTheatreSteps,
  PD_REASONING_THEATRE_STEPS,
  personadiaryPhaseToTheatreStep,
  playPdReasoningTheatreStepTone,
  type PdReasoningTheatreStep,
} from "@/lib/personadiaryReasoningTheatreV1";
import { usePersonadiaryDailyGuide } from "./usePersonadiaryDailyGuide";

const USER_DISCLAIMER =
  "[가설] 성찰 프리뷰입니다. 의료·투자·법률·실매매 결정을 대체하지 않습니다.";

const ORB_SIZE = 260;

export function PersonadiaryRitualDraw() {
  const { pkg } = usePersonadiaryDailyGuide();
  const [lut, setLut] = useState<RitualLutDoc | null>(null);
  const [bloom, setBloom] = useState<BloomSliceDoc | null>(null);
  const [lutError, setLutError] = useState(false);
  const [phase, setPhase] = useState<LatticePhase>("idle");
  const [breathPct, setBreathPct] = useState(0);
  const [convergePct, setConvergePct] = useState(0);
  const [question, setQuestion] = useState("");
  const [shatterTokens, setShatterTokens] = useState<string[]>([]);
  const [matchedHubs, setMatchedHubs] = useState<MatchedHub[]>([]);
  const [result, setResult] = useState<RitualDrawResult | null>(null);
  const [flipped, setFlipped] = useState(false);
  const [gateHint, setGateHint] = useState<string | null>(null);
  const [orbToneOn, setOrbToneOn] = useState(false);
  const [theatreSteps, setTheatreSteps] = useState<PdReasoningTheatreStep[]>(
    PD_REASONING_THEATRE_STEPS,
  );
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const breathStartRef = useRef(0);

  const clearTimers = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([fetchRitualLut(), fetchLatticeBloomSlice()]).then(([lutDoc, bloomDoc]) => {
      if (cancelled) return;
      if (!lutDoc) setLutError(true);
      else setLut(lutDoc);
      if (bloomDoc) setBloom(bloomDoc);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const saved = loadSessionDraw();
    if (!saved || !lut) return;
    const base = resolveLutCard(lut, saved.draw_token);
    if (!base) return;
    const merged = applyGuideOverlay(base, pkg);
    setQuestion(saved.question);
    setResult(merged);
    setPhase("done");
    setFlipped(true);
    if (bloom) {
      setMatchedHubs(rankBloomHubs(saved.question, bloom));
      setShatterTokens(shatterQuestionTokens(saved.question));
    }
  }, [lut, pkg, bloom]);

  useEffect(() => () => clearTimers(), [clearTimers]);

  const theatreStep = personadiaryPhaseToTheatreStep(phase);
  const theatreLayerOpacity =
    phase === "shatter" || phase === "vortex"
      ? 0.32
      : phase === "breath"
        ? 0.62
        : 1;

  const ritualStatus = useMemo((): { text: string; kind: "hint" | "warn" | "phase" } | null => {
    if (gateHint) return { text: gateHint, kind: "warn" };
    if (phase === "shatter") return { text: "분쇄 · 말 조각 분리…", kind: "phase" };
    if (phase === "vortex") return { text: "흡수 · 구슬 중심으로 수렴…", kind: "phase" };
    if (phase === "breath") {
      const sec = Math.ceil(((100 - breathPct) / 100) * (LATTICE_BREATH_MS / 1000));
      return { text: `호흡 맞추기… ${sec}초`, kind: "phase" };
    }
    if (phase === "converge") return { text: "공명 맵 정렬…", kind: "phase" };
    if (phase === "idle" || phase === "ready") {
      return { text: "질문을 적은 뒤 구슬을 터치하세요.", kind: "hint" };
    }
    return null;
  }, [gateHint, phase, breathPct]);

  useEffect(() => {
    if (!theatreStep) return;
    void playPdReasoningTheatreStepTone(theatreStep, orbToneOn);
  }, [phase, theatreStep, orbToneOn]);

  const runTimedPhase = useCallback(
    (from: LatticePhase, onComplete: () => void) => {
      const ms = latticePhaseDurationMs(from);
      if (ms <= 0) {
        onComplete();
        return;
      }
      timerRef.current = setTimeout(onComplete, ms);
    },
    []
  );

  const startBreathPhase = useCallback(() => {
    setPhase("breath");
    setBreathPct(0);
    breathStartRef.current = Date.now();
    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - breathStartRef.current;
      const pct = Math.min(100, Math.round((elapsed / LATTICE_BREATH_MS) * 100));
      setBreathPct(pct);
      if (elapsed >= LATTICE_BREATH_MS) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        intervalRef.current = null;
        setPhase("ready");
      }
    }, 80);
  }, []);

  const startLatticeGate = useCallback(() => {
    const q = question.trim();
    if (!q) {
      setGateHint("먼저 마음의 질문을 한 줄 적어 주세요.");
      return;
    }
    if (phase !== "idle" && phase !== "ready") return;
    setGateHint(null);
    clearTimers();
    void fetchMkmlifeReasoningTheatreSteps(q).then((remote) => {
      if (remote) setTheatreSteps(remote);
    });

    const tokens = shatterQuestionTokens(q);
    setShatterTokens(tokens);
    const hubs = bloom ? rankBloomHubs(q, bloom) : [];
    setMatchedHubs(hubs);

    setPhase("shatter");
    runTimedPhase("shatter", () => {
      setPhase("vortex");
      runTimedPhase("vortex", () => {
        startBreathPhase();
      });
    });
  }, [question, phase, bloom, clearTimers, runTimedPhase, startBreathPhase]);

  const runConvergeThenDraw = useCallback(
    (q: string, drawToken: string, merged: RitualDrawResult) => {
      setPhase("converge");
      setConvergePct(0);
      const start = Date.now();
      intervalRef.current = setInterval(() => {
        const elapsed = Date.now() - start;
        const pct = Math.min(100, Math.round((elapsed / LATTICE_CONVERGE_MS) * 100));
        setConvergePct(pct);
        if (elapsed >= LATTICE_CONVERGE_MS) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          intervalRef.current = null;
          setPhase("encapsulate");
          setResult(merged);
          setFlipped(false);
          window.setTimeout(() => {
            setFlipped(true);
            setPhase("done");
          }, 120);

          persistSessionDraw(merged, q);
          persistLatticeSession(
            buildLatticeSession({
              phase: "done",
              question_snippet: q.slice(0, 280),
              shatter_tokens: shatterTokens,
              matched_hub_ids: matchedHubs.map((h) => h.id),
              matched_hub_labels_ko: matchedHubs.map((h) => h.label_ko),
              draw_token: drawToken,
              encapsulation_card_id: merged.card.card_id,
            })
          );
          appendRitualDrawLog({
            schema: "personadiary_ritual_draw_log_v1",
            draw_token: drawToken,
            card_id: merged.card.card_id,
            atom_id: merged.card.atom_id,
            raw_lut_hit: merged.raw_lut_hit,
            repair_overlay_applied: merged.repair_overlay_applied,
            question_snippet: q.slice(0, 80),
            ts: new Date().toISOString(),
          });
        }
      }, 40);
    },
    [matchedHubs, shatterTokens]
  );

  function onSubmitDraw(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || !lut || phase !== "ready") return;

    const drawToken = randomDrawToken();
    const base = resolveLutCard(lut, drawToken);
    if (!base) return;

    const merged = applyGuideOverlay(base, pkg);
    if (bloom) {
      setMatchedHubs(rankBloomHubs(q, bloom));
    }
    runConvergeThenDraw(q, drawToken, merged);
  }

  const handoffUrl =
    result && question.trim()
      ? buildMkmlifeHandoffUrl(question.trim(), result.card.name_ko)
      : "https://mkmlife.com/ask-one";

  const questionLocked =
    phase === "shatter" ||
    phase === "vortex" ||
    phase === "breath" ||
    phase === "converge" ||
    phase === "encapsulate" ||
    phase === "done";

  const orbActive =
    phase === "idle" || (phase === "ready" && !result);

  return (
    <section className="pd-ritual-draw" aria-labelledby="pd-ritual-title">
      <div className="pd-ritual-draw-inner pd-glass">
        <p className="pd-ritual-kicker">
          <span className="pd-ritual-kicker-en">Lattice Convergence · Major 22</span>
          <span className="pd-ritual-kicker-hypo">[HYPO]</span>
        </p>
        <p className="pd-ritual-eyebrow">행운·리추얼 카드</p>
        <h2 id="pd-ritual-title">빛의 구슬 앞에서, 오늘 카드 한 장</h2>
        <p className="pd-ritual-lead">
          질문을 적고 구슬을 누르면 말 조각이 흡수된 뒤 공명 맵이 정렬됩니다. LLM 즉흥이
          아닌 LUT·읽기 전용 슬라이스 프리뷰입니다.
        </p>

        <div className="pd-ritual-orb-col">
          <div className="pd-ritual-orb-stack">
            <PersonadiaryMagicOrb
              size={ORB_SIZE}
              showLegend={false}
              showStatus={false}
              showTone
              onToneChange={setOrbToneOn}
              onOrbActivate={orbActive ? startLatticeGate : undefined}
              activateLabel="질문을 적은 뒤 구슬을 터치하세요"
            />
            {theatreStep ? (
              <PersonadiaryReasoningTheatre
                size={ORB_SIZE}
                activeStepId={theatreStep}
                steps={theatreSteps}
                breathPct={phase === "breath" ? breathPct : 0}
                layerOpacity={theatreLayerOpacity}
                className="pd-reasoning-theatre-overlay"
              />
            ) : null}
            <PersonadiaryLatticeOverlay
              size={ORB_SIZE}
              phase={phase}
              tokens={shatterTokens}
              matchedHubs={matchedHubs}
              convergePct={convergePct}
            />
          </div>
          <div
            className="pd-ritual-status-slot"
            data-testid="pd-ritual-status-slot"
            aria-live="polite"
            role="status"
          >
            {phase === "breath" ? (
              <div className="pd-ritual-breath">
                <div className="pd-ritual-breath-bar" aria-hidden>
                  <span style={{ width: `${breathPct}%` }} />
                </div>
                {ritualStatus ? (
                  <p className={`pd-ritual-status-line pd-ritual-status-line--${ritualStatus.kind}`}>
                    {ritualStatus.text}
                  </p>
                ) : null}
              </div>
            ) : ritualStatus ? (
              <p className={`pd-ritual-status-line pd-ritual-status-line--${ritualStatus.kind}`}>
                {ritualStatus.text}
              </p>
            ) : (
              <p className="pd-ritual-status-line pd-ritual-status-line--placeholder" aria-hidden="true">
                &nbsp;
              </p>
            )}
          </div>
        </div>

        {matchedHubs.length > 0 &&
        (phase === "ready" || phase === "converge" || phase === "encapsulate" || phase === "done") ? (
          <ul className="pd-lattice-mini-bloom" aria-label="공명 맵 미리보기">
            {matchedHubs.map((hub) => (
              <li key={hub.id}>
                <span className={`pd-lattice-dot pd-lattice-dot--${hub.kind}`} aria-hidden />
                {hub.label_ko}
              </li>
            ))}
          </ul>
        ) : null}

        <form className="pd-ritual-form" onSubmit={onSubmitDraw}>
          <label className="pd-ritual-form-label" htmlFor="pd-ritual-question">
            마음 모아 묻기 (한 가지)
          </label>
          <textarea
            id="pd-ritual-question"
            className="pd-reflect-input pd-ritual-question"
            rows={2}
            placeholder="예: 오늘 관계에서 내가 놓친 신호는?"
            value={question}
            disabled={questionLocked}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button
            type="submit"
            className="btn pd-btn-primary pd-ritual-submit"
            disabled={phase !== "ready" || !question.trim() || lutError}
          >
            오늘 카드 1장 뽑기
          </button>
        </form>

        {lutError ? (
          <p className="pd-guide-muted">LUT를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
        ) : null}

        {result && (phase === "done" || phase === "encapsulate") ? (
          <div
            className={`pd-ritual-card-reveal${flipped ? " is-flipped" : ""}`}
            role="status"
            aria-live="polite"
          >
            <article className="pd-ritual-tarot-card">
              <p className="pd-ritual-card-eyebrow">오늘의 성찰 카드 · preview_only</p>
              <h3>{result.card.name_ko}</h3>
              <p className="pd-ritual-card-en">{result.card.name_en}</p>
              <p className="pd-ritual-card-prompt">
                {sanitizeMomentLine(result.card.reflect_prompt_ko)}
              </p>
              {result.guide_overlay_ko ? (
                <p className="pd-ritual-card-overlay">
                  <span className="pd-ritual-card-overlay-label">오늘 가이드 맥락</span>
                  {sanitizeMomentLine(result.guide_overlay_ko)}
                </p>
              ) : null}
              <p className="pd-ritual-card-meta">{result.sasang_metaphor_ko}</p>
              <p className="pd-ritual-card-logos">{result.logos_hint_ko}</p>
              <p className="pd-ritual-card-metrics" aria-label="품질 원장">
                raw_lut_hit: {result.raw_lut_hit ? "1" : "0"} · repair_overlay:{" "}
                {result.repair_overlay_applied ? "1" : "0"}
              </p>
            </article>
            <div className="pd-ritual-handoff">
              <a
                className="btn btn-primary"
                href={handoffUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                더 깊은 리포트 · mkmlife 원퀘스천 (L2)
              </a>
              <p className="pd-ritual-handoff-note">
                PersonaDiary는 세션 한정 성찰만 보관합니다. 심화는 mkmlife로 이동합니다.
              </p>
            </div>
            <p className="pd-moment-disclaimer">{lut?.disclaimer_ko || USER_DISCLAIMER}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
