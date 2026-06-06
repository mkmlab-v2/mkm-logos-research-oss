"use client";



import { useState } from "react";

import {

  formatReflectFromGuide,

  usePersonadiaryDailyGuide,

} from "./usePersonadiaryDailyGuide";

import type { MomentResponse } from "@/lib/personadiaryMoment";

import {

  formatUserSummary,

  intentHeadlineKo,

  toDisplayMomentCards,

  USER_MOMENT_DISCLAIMER,

  sanitizeMomentLine,

} from "@/lib/personadiaryMomentDisplay";



const PRESET_TEXT: Record<string, string> = {

  meal: "오늘 점심 뭐 먹을까?",

  weather_fit: "오늘 날씨에 뭐 입을까?",

  mood: "지금 기분이 가라앉아서 마음을 정리하고 싶어.",

};



const MOMENTS = [

  { id: "meal", title: "점심 메뉴", sub: "날씨·명리 맥락으로 가볍게" },

  { id: "weather_fit", title: "오늘 옷·컬러", sub: "날씨와 체질 힌트" },

  { id: "mood", title: "지금 마음", sub: "감정·앵커 성찰" },

] as const;



export function PersonadiaryReflectTeaser() {

  const { pkg, profileId } = usePersonadiaryDailyGuide();

  const [query, setQuery] = useState("");

  const [moment, setMoment] = useState<MomentResponse | null>(null);

  const [fallbackText, setFallbackText] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);



  function applyPreset(id: string) {

    setQuery(PRESET_TEXT[id] || "");

    setMoment(null);

    setFallbackText(null);

  }



  async function onMoment() {

    const q = query.trim();

    if (!q) return;

    setBusy(true);

    setMoment(null);

    setFallbackText(null);

    try {

      const res = await fetch("/api/personadiary/moment", {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({ text: q, profile_id: profileId }),

      });

      const data = await res.json();

      if (res.ok && data.ok && data.moment) {

        setMoment(data.moment as MomentResponse);

        return;

      }

      const reflectRes = await fetch("/api/personadiary/reflect", {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({ text: q, profile_id: profileId }),

      });

      const reflectData = await reflectRes.json();

      if (reflectRes.ok && reflectData.ok && reflectData.reflection_ko) {

        setFallbackText(String(reflectData.reflection_ko));

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



  const displayCards = moment
    ? toDisplayMomentCards(moment.cards, 2, moment.intent)
    : [];

  const extraCards = moment ? moment.cards.slice(2) : [];



  return (

    <div className="pd-reflect-teaser">

      <p className="pd-reflect-label">찰나의 나 · 순간 질문</p>

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

        disabled={busy}

        onClick={onMoment}

      >

        {busy ? "찰나의 판을 읽는 중…" : "순간 답 받기"}

      </button>



      {moment ? (

        <div className="pd-moment-result" role="status" aria-live="polite">

          <p className="pd-moment-result-eyebrow">

            {intentHeadlineKo(moment.intent)}

            {moment.calendar_kst ? ` · ${moment.calendar_kst}` : ""}

          </p>

          <p className="pd-moment-result-lead">

            {formatUserSummary(moment.summary_ko_polished || moment.summary_ko)}

          </p>

          {moment.summary_ko_polished ? (

            <p className="pd-moment-polish-note">[가설] Ollama 다듬기 · 미리보기</p>

          ) : null}

          {displayCards.length > 0 ? (

            <div className="pd-moment-result-cards">

              {displayCards.map((card) => (

                <article

                  key={card.title_ko}

                  className="pd-moment-result-card"

                >

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

          <details className="pd-moment-dev">

            <summary>미리보기 메타</summary>

            <p className="pd-moment-dev-meta">

              intent:{moment.intent} · preview_only · {moment.calendar_kst}

            </p>

          </details>

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

