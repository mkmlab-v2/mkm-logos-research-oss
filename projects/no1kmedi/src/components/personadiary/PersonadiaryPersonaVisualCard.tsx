"use client";

import { useCallback, useState } from "react";
import { buildPersonaVisualCardView } from "@/lib/personadiaryPersonaVisualCardV1";
import { usePersonadiaryDailyGuide } from "./usePersonadiaryDailyGuide";

export function PersonadiaryPersonaVisualCard() {
  const { pkg, loading } = usePersonadiaryDailyGuide();
  const view = buildPersonaVisualCardView(pkg);
  const [shareHint, setShareHint] = useState<string | null>(null);

  const onShare = useCallback(async () => {
    if (!view) return;
    const text = view.share_text_ko;
    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        await navigator.share({
          title: `Persona Diary · ${view.calendar_kst}`,
          text,
        });
        setShareHint("공유 창을 열었어요");
        return;
      }
      await navigator.clipboard.writeText(text);
      setShareHint("카드 문구를 복사했어요");
    } catch {
      setShareHint("공유를 건너뛰었어요");
    }
    window.setTimeout(() => setShareHint(null), 2400);
  }, [view]);

  return (
    <section
      className="pd-persona-visual-section"
      aria-labelledby="pd-persona-visual-title"
      data-testid="pd-persona-visual-section"
    >
      <div className="pd-premium-section-inner">
        <p id="pd-persona-visual-title" className="pd-ios-group-label">
          페르소나 비주얼 카드
        </p>
        <p className="pd-persona-visual-lead">
          오늘의 찰나를 한 장의 카드로 — AI 일러스트 전 단계, CSS 스냅샷 프리뷰
        </p>
        <span className="pd-persona-visual-ssot" hidden aria-hidden>
          persona-visual-card-v1 design-kernel-v1 moment-bundle-v1
        </span>

        {loading ? (
          <p className="pd-persona-visual-loading">카드를 그리는 중…</p>
        ) : !view ? (
          <p className="pd-persona-visual-fallback">오늘 카드는 준비 중이에요.</p>
        ) : (
          <article
            className="pd-persona-visual-card pd-persona-visual-card--kernel-v1"
            data-testid="pd-persona-visual-card"
            data-design-kernel-version={view.design_kernel.kernel_version}
            data-pathology-state={view.design_kernel.pathology_state}
            data-moment-bundle-id={view.moment_bundle.moment_bundle_id}
            data-bgm-fallback={view.moment_bundle.bgm_fallback}
            data-motion-cap={view.design_kernel.motion_cap >= 0.5 ? "high" : "low"}
            style={
              {
                "--pd-pvc-from": view.palette.gradient_from,
                "--pd-pvc-to": view.palette.gradient_to,
                "--pd-pvc-accent": view.palette.accent,
                "--pd-pvc-orb": view.palette.orb,
                "--pd-pvc-motion-cap": String(view.design_kernel.motion_cap),
                "--pd-pvc-pulse-period": `${view.design_kernel.pulse_period_ms}ms`,
                "--pd-pvc-intensity": String(view.design_kernel.intensity_budget),
              } as React.CSSProperties
            }
          >
            <div className="pd-persona-visual-orb" aria-hidden />
            <header className="pd-persona-visual-header">
              <span className="pd-persona-visual-date">{view.calendar_kst}</span>
              <span className="pd-persona-visual-city">{view.city_label}</span>
            </header>
            <h2 className="pd-persona-visual-title">{view.title_ko}</h2>
            <p className="pd-persona-visual-acode">
              {view.acode_public} · {view.acode_title}
            </p>
            <p className="pd-persona-visual-subtitle">{view.subtitle_ko}</p>
            <p className="pd-persona-visual-keyword">{view.keyword_ko}</p>
            <p className="pd-persona-visual-fusion">{view.fusion_line}</p>
            <div className="pd-persona-visual-meta">
              <span>🌤 {view.world_weather}</span>
              <span>✨ {view.me_line}</span>
            </div>
            <p className="pd-persona-visual-delight">🍲 {view.delight_chip}</p>
            <footer className="pd-persona-visual-watermark">{view.watermark_ko}</footer>
          </article>
        )}

        <div className="pd-persona-visual-actions">
          <button
            type="button"
            className="btn btn-primary"
            disabled={!view}
            onClick={() => void onShare()}
          >
            카드 공유하기
          </button>
          {shareHint ? <p className="pd-persona-visual-hint">{shareHint}</p> : null}
        </div>
      </div>
    </section>
  );
}
