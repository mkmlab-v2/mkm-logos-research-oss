"use client";

import { usePersonadiaryDailyGuide } from "./usePersonadiaryDailyGuide";

export function PersonadiaryDailyGuideCards() {
  const { pkg, loading, error } = usePersonadiaryDailyGuide();

  if (loading) {
    return <p className="pd-guide-loading">오늘의 가이드를 불러오는 중…</p>;
  }
  if (error || !pkg?.ui_blocks?.length) {
    return (
      <p className="pd-guide-muted">
        오늘의 융합 가이드는 준비 중입니다. 미리보기 프리셋으로 성찰해 보세요.
      </p>
    );
  }

  const hero = pkg.ui_blocks?.find((b) => b.type === "hero");
  const cards = pkg.ui_blocks?.filter(
    (b) =>
      b.type === "card" ||
      b.type === "verse" ||
      b.type === "world_pulse" ||
      b.type === "hypothesis_stream" ||
      b.type === "user_condition"
  );

  return (
    <div className="pd-daily-guide">
      <p className="pd-reflect-label">
        오늘의 마음 가이드 · {pkg.calendar_kst || "—"}
      </p>
      {hero ? (
        <article className="pd-guide-hero pd-glass">
          <h3>{hero.title_ko}</h3>
          <p className="pd-guide-hero-body">{hero.body_ko}</p>
          {hero.badge_ko ? (
            <span className="pd-reflect-tag">{hero.badge_ko}</span>
          ) : null}
        </article>
      ) : null}
      <div className="pd-guide-grid">
        {(cards ?? [])
          .slice(0, 5)
          .map((block) => (
            <article key={`${block.type}-${block.title_ko}`} className="pd-guide-card pd-glass">
              <h4>{block.title_ko}</h4>
              {block.ref ? <p className="pd-guide-ref">{block.ref}</p> : null}
              <p>{block.body_ko}</p>
              {block.badge_ko ? (
                <span className="pd-reflect-tag">{block.badge_ko}</span>
              ) : null}
            </article>
          ))}
      </div>
    </div>
  );
}
