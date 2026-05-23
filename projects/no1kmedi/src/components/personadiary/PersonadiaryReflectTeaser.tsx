"use client";

import { useState } from "react";
import {
  formatReflectFromGuide,
  usePersonadiaryDailyGuide,
} from "./usePersonadiaryDailyGuide";

const PRESET_TEXT: Record<string, string> = {
  transition: "큰 변화가 다가올 때, 두려움보다 숨 고르기를 먼저 적어 봅니다.",
  crossroads: "갈림길에서 각 선택이 나에게 주는 평온과 부담을 나란히 적어 봅니다.",
  gratitude: "오늘 고마웠던 순간 세 가지를 짧게 적어 마음을 정리합니다.",
};

const MOMENTS = [
  { id: "transition", title: "큰 전환 앞", sub: "마음을 가볍게 정리하고 싶을 때" },
  { id: "crossroads", title: "갈림길", sub: "선택의 이유를 차분히 적어 볼 때" },
  { id: "gratitude", title: "오늘 하루", sub: "감사한 순간 세 가지" },
] as const;

export function PersonadiaryReflectTeaser() {
  const { pkg, profileId } = usePersonadiaryDailyGuide();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function applyPreset(id: string) {
    setQuery(PRESET_TEXT[id] || "");
    setResult(null);
  }

  async function onReflect() {
    const q = query.trim();
    if (!q) return;
    setBusy(true);
    setResult(null);
    try {
      const res = await fetch("/api/personadiary/reflect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: q, profile_id: profileId }),
      });
      const data = await res.json();
      if (res.ok && data.ok && data.reflection_ko) {
        setResult(String(data.reflection_ko));
      } else {
        setResult(
          formatReflectFromGuide(pkg?.reflect_template_ko, q) ||
            "가이드를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
        );
      }
    } catch {
      setResult(formatReflectFromGuide(pkg?.reflect_template_ko, q));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pd-reflect-teaser">
      <p className="pd-reflect-label">오늘의 순간</p>
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
        placeholder="지금 마음을 한두 문장으로 적어 주세요…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button
        type="button"
        className="btn btn-primary pd-reflect-submit"
        disabled={busy}
        onClick={onReflect}
      >
        {busy ? "마음을 담는 중…" : "구슬에 마음 남기기"}
      </button>
      {result ? (
        <div className="pd-reflect-result" role="status">
          <p className="pd-reflect-tag">[가설] · NON_GATING · preview_only</p>
          <p>{result}</p>
        </div>
      ) : null}
    </div>
  );
}
