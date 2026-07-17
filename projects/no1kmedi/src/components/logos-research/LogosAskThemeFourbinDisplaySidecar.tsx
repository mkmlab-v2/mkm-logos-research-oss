"use client";

import { useEffect, useMemo, useState } from "react";

import {
  THEME_FOURBIN_ASK_DISPLAY_URL,
  THEME_FOURBIN_ASK_DISPLAY_V,
  THEME_FOURBIN_LAYOUT_SLOT,
  THEME_FOURBIN_PATH_TAB,
  THEME_FOURBIN_SIBLING_OF,
  assertNoGematriaLeakInDisplay,
  binLabelKo,
  isLogosAskThemeFourbinDisplayV1Enabled,
  resolveThemeFourbinDisplayVerse,
  sortedBinEntries,
  type ThemeFourbinAskDisplayDocV1,
  type ThemeFourbinVerseRowV1,
} from "@/lib/logosAskThemeFourbinDisplayV1";

type Props = {
  verseRefs: string[];
  query?: string;
  /** S4 / answer body — enables on-answer live score when fixture miss. */
  answerText?: string;
  /** When set, force a demo verse id (preview / smoke). */
  forceVerseId?: string | null;
  /** Optional preloaded doc (preview / SSR) — skips network when provided. */
  initialDoc?: ThemeFourbinAskDisplayDocV1 | null;
  /** Mainline heart: show even without verseRefs if query/answer present. */
  alwaysOnMainline?: boolean;
};

function FrameBinBars({
  frame,
  dominant,
  weights,
}: {
  frame: "a" | "b";
  dominant?: string | null;
  weights?: Record<string, number> | null;
}) {
  const entries = sortedBinEntries(weights).slice(0, 4);
  if (!entries.length) {
    return <p className="lr-ask-muted lr-ask-theme-fourbin-empty">—</p>;
  }
  return (
    <ul className="lr-ask-theme-fourbin-bins" data-lr-ask-theme-frame={frame}>
      {entries.map(({ bin, weight }) => {
        const pct = Math.max(0, Math.min(100, Math.round(weight * 100)));
        const active = bin === dominant;
        return (
          <li
            key={`${frame}-${bin}`}
            className={`lr-ask-theme-fourbin-bin${active ? " lr-ask-theme-fourbin-bin--dominant" : ""}`}
            data-bin={bin}
            data-dominant={active ? "1" : "0"}
          >
            <span className="lr-ask-theme-fourbin-bin-label">{binLabelKo(frame, bin)}</span>
            <span className="lr-ask-theme-fourbin-bin-track" aria-hidden="true">
              <span className="lr-ask-theme-fourbin-bin-fill" style={{ width: `${pct}%` }} />
            </span>
            <span className="lr-ask-theme-fourbin-bin-pct">{pct}%</span>
          </li>
        );
      })}
    </ul>
  );
}

export function LogosAskThemeFourbinDisplaySidecar({
  verseRefs,
  query = "",
  answerText = "",
  forceVerseId = null,
  initialDoc = null,
  alwaysOnMainline = false,
}: Props) {
  const enabled = isLogosAskThemeFourbinDisplayV1Enabled();
  const [doc, setDoc] = useState<ThemeFourbinAskDisplayDocV1 | null>(initialDoc);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    if (initialDoc) {
      setDoc(initialDoc);
      setLoadError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${THEME_FOURBIN_ASK_DISPLAY_URL}?v=${THEME_FOURBIN_ASK_DISPLAY_V}`,
          { cache: "no-store" },
        );
        if (!res.ok) throw new Error(`theme_fourbin_http_${res.status}`);
        const data = (await res.json()) as ThemeFourbinAskDisplayDocV1;
        if (cancelled) return;
        if (data.address_book_merge !== false) {
          setLoadError("address_book_merge_wall");
          return;
        }
        setDoc(data);
        setLoadError(null);
      } catch (e: unknown) {
        if (cancelled) return;
        setLoadError(e instanceof Error ? e.message : "theme_fourbin_load_failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [enabled, initialDoc]);

  const verse: ThemeFourbinVerseRowV1 | null = useMemo(() => {
    if (!doc) return null;
    if (forceVerseId) {
      const forced = doc.verses.find((v) => v.id === forceVerseId) ?? null;
      if (!forced) return null;
      return {
        ...forced,
        theme_fourbin_display: forced.theme_fourbin_display
          ? { ...forced.theme_fourbin_display, source: "fixture" as const }
          : undefined,
      };
    }
    return resolveThemeFourbinDisplayVerse(doc, verseRefs, query, answerText);
  }, [answerText, doc, forceVerseId, query, verseRefs]);

  if (!enabled) return null;
  const hasSignal =
    forceVerseId ||
    verseRefs.length > 0 ||
    Boolean(query.trim()) ||
    Boolean(answerText.trim());
  if (!hasSignal && !alwaysOnMainline) return null;
  if (loadError) {
    return (
      <aside
        className="lr-ask-theme-fourbin-sidecar lr-ask-theme-fourbin-sidecar--error"
        data-logos-ask-theme-fourbin="1"
        data-logos-ask-theme-fourbin-mainline="1"
        data-layout-slot={THEME_FOURBIN_LAYOUT_SLOT}
        data-sibling-of={THEME_FOURBIN_SIBLING_OF}
        data-path-tab={THEME_FOURBIN_PATH_TAB}
        data-address-book-merge="false"
        data-load-error={loadError}
        aria-label="테마 4칸 (로드 실패)"
      >
        <p className="lr-ask-muted">테마 4칸 표시를 잠시 불러오지 못했습니다.</p>
      </aside>
    );
  }
  if (!doc) {
    return (
      <aside
        className="lr-ask-theme-fourbin-sidecar lr-ask-theme-fourbin-sidecar--loading"
        data-logos-ask-theme-fourbin="1"
        data-logos-ask-theme-fourbin-mainline="1"
        data-layout-slot={THEME_FOURBIN_LAYOUT_SLOT}
        data-sibling-of={THEME_FOURBIN_SIBLING_OF}
        data-path-tab={THEME_FOURBIN_PATH_TAB}
        data-address-book-merge="false"
        aria-busy="true"
        aria-label="테마 4칸 로딩"
      >
        <p className="lr-ask-muted">테마 4칸 불러오는 중…</p>
      </aside>
    );
  }
  if (!verse?.theme_fourbin_display) {
    if (!alwaysOnMainline) return null;
    return (
      <aside
        className="lr-ask-theme-fourbin-sidecar lr-ask-theme-fourbin-sidecar--empty"
        data-logos-ask-theme-fourbin="1"
        data-logos-ask-theme-fourbin-mainline="1"
        data-layout-slot={THEME_FOURBIN_LAYOUT_SLOT}
        data-path-tab={THEME_FOURBIN_PATH_TAB}
        data-address-book-merge="false"
        data-send-gate="HOLD"
        aria-label="테마 4칸 (신호 대기)"
      >
        <p className="lr-ask-muted">답변이 쌓이면 테마 4칸이 여기에 표시됩니다.</p>
      </aside>
    );
  }

  const disp = verse.theme_fourbin_display;
  if (!assertNoGematriaLeakInDisplay(disp)) {
    return (
      <aside
        className="lr-ask-theme-fourbin-sidecar lr-ask-theme-fourbin-sidecar--error"
        data-logos-ask-theme-fourbin="1"
        data-layout-slot={THEME_FOURBIN_LAYOUT_SLOT}
        data-wall="gematria_leak_blocked"
        aria-label="테마 4칸 (격벽)"
      >
        <p className="lr-ask-muted">표시 필드 격벽으로 숨김 (gematria 합선 금지).</p>
      </aside>
    );
  }

  const fa = disp.frame_a;
  const fb = disp.frame_b;
  const explain = (disp.explain_ab_differ_ko ?? []).slice(0, 2);
  const source = disp.source ?? "fixture";

  return (
    <aside
      className="lr-ask-theme-fourbin-sidecar"
      data-logos-ask-theme-fourbin="1"
      data-logos-ask-theme-fourbin-mainline="1"
      data-layout-slot={THEME_FOURBIN_LAYOUT_SLOT}
      data-sibling-of={THEME_FOURBIN_SIBLING_OF}
      data-path-tab={THEME_FOURBIN_PATH_TAB}
      data-address-book-merge="false"
      data-verse-id={verse.id}
      data-display-source={source}
      data-frame-a-dominant={fa?.dominant_bin ?? ""}
      data-frame-b-dominant={fb?.dominant_bin ?? ""}
      data-send-gate="HOLD"
      data-research-only="1"
      aria-label="테마 4칸 의미망 (표시 전용 · 연구 참고)"
    >
      <div className="lr-ask-theme-fourbin-head">
        <p className="lr-ask-theme-fourbin-label">테마 4칸 · 표시 전용</p>
        <p className="lr-ask-theme-fourbin-meta">
          {verse.label_ko ?? verse.id}
          {source === "live_score" ? " · 라이브" : ""} · gematria 합선 없음
        </p>
      </div>

      <div className="lr-ask-theme-fourbin-frames">
        <section className="lr-ask-theme-fourbin-frame" data-frame="a">
          <h4 className="lr-ask-theme-fourbin-frame-title">
            Frame A · 구원사
            {fa?.dominant_bin ? (
              <span className="lr-ask-theme-fourbin-dominant">
                {binLabelKo("a", fa.dominant_bin)}
              </span>
            ) : null}
          </h4>
          <FrameBinBars frame="a" dominant={fa?.dominant_bin} weights={fa?.bin_weights} />
        </section>
        <section className="lr-ask-theme-fourbin-frame" data-frame="b">
          <h4 className="lr-ask-theme-fourbin-frame-title">
            Frame B · 제도
            {fb?.dominant_bin ? (
              <span className="lr-ask-theme-fourbin-dominant">
                {binLabelKo("b", fb.dominant_bin)}
              </span>
            ) : null}
          </h4>
          <FrameBinBars frame="b" dominant={fb?.dominant_bin} weights={fb?.bin_weights} />
        </section>
      </div>

      {explain.length ? (
        <ul className="lr-ask-theme-fourbin-explain">
          {explain.map((line) => (
            <li key={line.slice(0, 48)}>{line}</li>
          ))}
        </ul>
      ) : null}

      <p className="lr-ask-theme-fourbin-wall" role="note">
        research_only · SEND HOLD · address_book_merge=false · Final Action 아님
      </p>
    </aside>
  );
}
