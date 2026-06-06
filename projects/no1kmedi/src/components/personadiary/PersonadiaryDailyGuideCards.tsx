"use client";

import { useState } from "react";
import { usePersonadiaryDailyGuide } from "./usePersonadiaryDailyGuide";
import { sanitizeGuideBody } from "@/lib/personadiaryMomentDisplay";
import { PersonadiaryFeedbackStrip } from "./PersonadiaryFeedbackStrip";
import type { DailyGuideBlock } from "@/lib/personadiaryDailyGuide";

const BODY_RHYTHM_PREFIX = "몸·리듬 —";

function isBodyRhythmCard(block: DailyGuideBlock): boolean {
  return block.type === "card" && (block.title_ko?.startsWith(BODY_RHYTHM_PREFIX) ?? false);
}

function evidenceTierLabel(tier?: string): string | null {
  if (tier === "literature_supported") return "문헌";
  if (tier === "coaching_heuristic") return "코칭";
  if (tier === "delight") return "스타일";
  return null;
}

export function PersonadiaryDailyGuideCards() {
  const { pkg, loading, error, profileId } = usePersonadiaryDailyGuide();
  const [expanded, setExpanded] = useState(false);
  const [bodyRhythmOpen, setBodyRhythmOpen] = useState(true);

  if (loading) {
    return <p className="pd-guide-loading">오늘의 가이드를 불러오는 중…</p>;
  }
  if (error || !pkg?.ui_blocks?.length) {
    return (
      <p className="pd-guide-muted">
        {error === "timeout"
          ? "가이드 로딩이 지연되고 있습니다. 순간 질문은 아래에서 바로 체험해 보세요."
          : "오늘의 융합 가이드는 준비 중입니다. 위에서 순간 질문으로 먼저 체험해 보세요."}
      </p>
    );
  }

  const heroPolish = pkg.moment_preset_polish_v1?.hero?.body_ko_polished?.trim();
  const hero = pkg.ui_blocks?.find((b) => b.type === "hero");
  const newsMeHypo = pkg.ui_blocks?.find((b) => b.type === "news_me_hypo");
  const bodyRhythmCards =
    pkg.ui_blocks?.filter((b) => isBodyRhythmCard(b)) ?? [];
  const cards = pkg.ui_blocks?.filter(
    (b) =>
      (b.type === "card" ||
        b.type === "verse" ||
        b.type === "world_pulse" ||
        b.type === "hypothesis_stream" ||
        b.type === "user_condition") &&
      !isBodyRhythmCard(b)
  );
  const bodyRhythmTeaser = bodyRhythmCards[0]?.body_ko?.split("\n")[0]?.trim();

  return (
    <div className="pd-daily-guide">
      <p className="pd-reflect-label pd-daily-guide-label">
        오늘의 마음 가이드 · {pkg.calendar_kst || "—"}
      </p>
      {hero ? (
        <article className="pd-guide-hero pd-glass">
          <h3>{hero.title_ko}</h3>
          <p className="pd-guide-hero-body">
            {heroPolish || sanitizeGuideBody(hero.body_ko ?? "", 200)}
          </p>
        </article>
      ) : null}

      {bodyRhythmCards.length > 0 && !expanded && bodyRhythmTeaser ? (
        <p className="pd-body-rhythm-teaser">
          <span className="pd-body-rhythm-teaser-label">몸·리듬</span>
          {sanitizeGuideBody(bodyRhythmTeaser, 100)}
        </p>
      ) : null}

      <button
        type="button"
        className="pd-guide-expand"
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
      >
        {expanded ? "가이드 접기" : "오늘 가이드 더 보기"}
      </button>

      {expanded ? (
        <div className="pd-guide-expanded">
          {newsMeHypo ? (
            <article className="pd-guide-hero pd-guide-news-me pd-glass">
              <h3>{newsMeHypo.title_ko}</h3>
              <p className="pd-guide-hero-body">
                {sanitizeGuideBody(newsMeHypo.body_ko ?? "", 280)}
              </p>
              {newsMeHypo.mkmlife_href ? (
                <p className="pd-guide-mkmlife-link">
                  <a href={newsMeHypo.mkmlife_href} rel="noopener noreferrer">
                    mkmlife 원퀘스천 · oracle-sphere →
                  </a>
                </p>
              ) : null}
            </article>
          ) : null}

          {bodyRhythmCards.length > 0 ? (
            <section className="pd-body-rhythm-section pd-glass">
              <button
                type="button"
                className="pd-body-rhythm-toggle"
                aria-expanded={bodyRhythmOpen}
                onClick={() => setBodyRhythmOpen((v) => !v)}
              >
                <span className="pd-body-rhythm-heading">
                  몸·리듬 (식사·움직임·호흡·옷·공간)
                </span>
                <span className="pd-body-rhythm-badge">[가설][웰니스]</span>
                <span className="pd-body-rhythm-chevron" aria-hidden>
                  {bodyRhythmOpen ? "▾" : "▸"}
                </span>
              </button>
              {bodyRhythmOpen ? (
                <div className="pd-body-rhythm-grid">
                  {bodyRhythmCards.map((block) => {
                    const tier = evidenceTierLabel(block.evidence_tier);
                    const menuTitle = block.title_ko.replace(BODY_RHYTHM_PREFIX, "").trim();
                    return (
                      <article
                        key={`br-${block.title_ko}`}
                        className="pd-body-rhythm-card"
                      >
                        <h4>
                          {menuTitle}
                          {tier ? (
                            <span className="pd-body-rhythm-tier">{tier}</span>
                          ) : null}
                        </h4>
                        <p className="pd-body-rhythm-card-body">
                          {sanitizeGuideBody(block.body_ko ?? "", 220)}
                        </p>
                      </article>
                    );
                  })}
                </div>
              ) : null}
              <p className="pd-body-rhythm-disclaimer">
                진단·처방·체중 보장 없음. 부분 감량 불가 — 전신 활동·식이 패턴 우선.
              </p>
            </section>
          ) : null}

          <div className="pd-guide-grid">
            {(cards ?? []).slice(0, 5).map((block) => (
              <article
                key={`${block.type}-${block.title_ko}`}
                className="pd-guide-card pd-glass"
              >
                <h4>{block.title_ko}</h4>
                {block.ref ? <p className="pd-guide-ref">{block.ref}</p> : null}
                <p className="pd-guide-card-body">
                  {sanitizeGuideBody(block.body_ko ?? "", 140)}
                </p>
              </article>
            ))}
          </div>
        </div>
      ) : null}

      <PersonadiaryFeedbackStrip
        profileId={profileId}
        calendarKst={pkg.calendar_kst}
      />
    </div>
  );
}
