"use client";

import { useEffect, useState } from "react";
import type { MomentResponse } from "@/lib/personadiaryMoment";
import {
  canAskMoment,
  consumeMomentQuota,
  getMomentQuotaState,
  type MomentQuotaState,
} from "@/lib/personadiaryMomentQuotaV1";
import { getOrCreatePersonadiaryUserId, surveyResponsesForAcodeDerive } from "@/lib/personadiaryConsumerProfileV1";
import {
  formatUserSummary,
  intentHeadlineKo,
  sanitizeMomentLine,
  toDisplayMomentCards,
  USER_MOMENT_DISCLAIMER,
} from "@/lib/personadiaryMomentDisplay";
import { formatReflectFromGuide, usePersonadiaryDailyGuide } from "./usePersonadiaryDailyGuide";

const PRESET_TEXT: Record<string, string> = {
  meal: "오늘 점심 뭐 먹을까?",
  weather_fit: "오늘 날씨에 뭐 입을까?",
  mood: "지금 기분이 가라앉아서 마음을 정리하고 싶어.",
  world_me: "오늘 뉴스 보니 마음이 복잡해 — 세상과 나는 어떻게 맞춰 가면 좋을까?",
};

const MOMENTS = [
  { id: "meal", title: "점심 메뉴", sub: "A-Code·날씨·뉴스·찰나 맞춤" },
  { id: "weather_fit", title: "오늘 옷·컬러", sub: "체감 날씨 맞춤" },
  { id: "mood", title: "지금 마음", sub: "가볍게 돌보기" },
  { id: "world_me", title: "세상과 나", sub: "뉴스·거시 한 줄" },
] as const;

export function PersonadiaryReflectTeaser() {
  const { pkg } = usePersonadiaryDailyGuide();
  const [query, setQuery] = useState("");
  const [moment, setMoment] = useState<MomentResponse | null>(null);
  const [fallbackText, setFallbackText] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [quota, setQuota] = useState<MomentQuotaState | null>(null);
  const [quotaBlock, setQuotaBlock] = useState<string | null>(null);

  useEffect(() => {
    setQuota(getMomentQuotaState());
  }, []);

  function applyPreset(id: string) {
    setQuery(PRESET_TEXT[id] || "");
    setMoment(null);
    setFallbackText(null);
    setQuotaBlock(null);
  }

  async function onMoment() {
    const q = query.trim();
    if (!q) return;
    if (!canAskMoment()) {
      setQuotaBlock(
        `오늘 무료 찰나 질문 ${getMomentQuotaState().limit}회를 모두 썼어요. Plus에서 무제한(준비 중) · 내일 다시 만나요.`
      );
      return;
    }

    setBusy(true);
    setMoment(null);
    setFallbackText(null);
    setQuotaBlock(null);

    try {
      const momentProfileId = getOrCreatePersonadiaryUserId();
      const surveyResponses = surveyResponsesForAcodeDerive();
      const res = await fetch("/api/personadiary/moment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: q,
          profile_id: momentProfileId,
          ...(surveyResponses ? { survey_responses: surveyResponses } : {}),
        }),
      });
      const data = await res.json();
      if (res.ok && data.ok && data.moment) {
        setMoment(data.moment as MomentResponse);
        setQuota(consumeMomentQuota());
        return;
      }

      const reflectRes = await fetch("/api/personadiary/reflect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: q, profile_id: momentProfileId }),
      });
      const reflectData = await reflectRes.json();
      if (reflectRes.ok && reflectData.ok && reflectData.reflection_ko) {
        setFallbackText(String(reflectData.reflection_ko));
        setQuota(consumeMomentQuota());
      } else {
        setFallbackText(
          formatReflectFromGuide(pkg?.reflect_template_ko, q) ||
            "가이드를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
        );
      }
    } catch {
      setFallbackText(formatReflectFromGuide(pkg?.reflect_template_ko, q));
    } finally {
      setBusy(false);
    }
  }

  const displayCards = moment ? toDisplayMomentCards(moment.cards, 2, moment.intent) : [];
  const extraCards = moment ? moment.cards.slice(2) : [];

  return (
    <div className="pd-reflect-teaser" data-testid="pd-reflect-teaser">
      <span className="pd-moment-quota-ssot" hidden aria-hidden>
        pd-moment-quota-v1
      </span>
      <p className="pd-reflect-label">찰나 질문 · 하루 {quota?.limit ?? 3}회 무료</p>
      {quota ? (
        <p className="pd-moment-quota" data-testid="pd-moment-quota-v1">
          오늘 남은 찰나 질문 <strong>{quota.remaining}</strong> / {quota.limit}
        </p>
      ) : null}

      <div className="pd-moment-grid">
        {MOMENTS.map((m) => (
          <button
            key={m.id}
            type="button"
            className="pd-moment-card"
            onClick={() => applyPreset(m.id)}
          >
            <strong>{m.title}</strong>
            <span>{m.sub}</span>
          </button>
        ))}
      </div>

      <textarea
        className="pd-reflect-input"
        rows={3}
        placeholder="예: 오늘 점심 뭐 먹을까? · 날씨에 맞는 옷은?"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      <button
        type="button"
        className="btn pd-btn-primary pd-reflect-submit"
        disabled={busy || quota?.at_limit}
        onClick={() => void onMoment()}
      >
        {busy ? "찰나의 판을 읽는 중…" : "순간 답 받기"}
      </button>

      {quotaBlock ? (
        <p className="pd-moment-quota-block" role="status">
          {quotaBlock}
        </p>
      ) : null}

      {moment ? (
        <div className="pd-moment-result" role="status" aria-live="polite">
          <p className="pd-moment-result-eyebrow">
            {intentHeadlineKo(moment.intent)}
            {moment.calendar_kst ? ` · ${moment.calendar_kst}` : ""}
          </p>
          {moment.acode_persona ? (
            <p className="pd-moment-result-acode">
              {moment.acode_persona.public_code} · {moment.acode_persona.title_ko}
            </p>
          ) : null}
          <p className="pd-moment-result-lead">
            {formatUserSummary(moment.summary_ko_polished || moment.summary_ko)}
          </p>
          {moment.summary_ko_polished ? (
            <p className="pd-moment-polish-note">
              [가설] 다듬기 ·{" "}
              {moment.polish_meta?.backend === "azure_openai"
                ? "Azure"
                : moment.polish_meta?.backend === "ollama"
                  ? "Ollama"
                  : "다듬기"}
              {" · "}미리보기
            </p>
          ) : null}
          {displayCards.length > 0 ? (
            <div className="pd-moment-result-cards">
              {displayCards.map((card) => (
                <article key={card.title_ko} className="pd-moment-result-card">
                  <h4>{card.title_ko}</h4>
                  <ul>
                    {card.bullets.map((bullet) => (
                      <li key={bullet.slice(0, 40)}>{bullet}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          ) : null}
          {extraCards.length > 0 ? (
            <details className="pd-moment-more">
              <summary>맥락 더 보기 ({extraCards.length})</summary>
              <ul className="pd-moment-more-list">
                {extraCards.map((card) => (
                  <li key={card.section_id}>
                    <strong>{card.title_ko}</strong>
                    <p>{sanitizeMomentLine(card.body_ko.slice(0, 280))}</p>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
          <p className="pd-moment-disclaimer">{USER_MOMENT_DISCLAIMER}</p>
        </div>
      ) : null}

      {fallbackText ? (
        <div className="pd-moment-result pd-moment-result--fallback" role="status">
          <p className="pd-moment-result-eyebrow">가벼운 성찰</p>
          <p className="pd-moment-result-lead">{sanitizeMomentLine(fallbackText)}</p>
          <p className="pd-moment-disclaimer">{USER_MOMENT_DISCLAIMER}</p>
        </div>
      ) : null}
    </div>
  );
}
