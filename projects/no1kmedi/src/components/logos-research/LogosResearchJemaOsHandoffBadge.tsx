"use client";

import { useEffect, useState } from "react";

import {
  fetchLogosJemaAiResearchHandoff,
  type LogosJemaAiResearchHandoffV1,
} from "@/lib/logosJemaAiResearchHandoffV1";

export function LogosResearchJemaOsHandoffBadge() {
  const [handoff, setHandoff] = useState<LogosJemaAiResearchHandoffV1 | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchLogosJemaAiResearchHandoff().then((doc) => {
      if (!cancelled) setHandoff(doc);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!handoff) return null;

  const surface = handoff.surface ?? {};
  const gov = handoff.governance ?? {};
  const consumer = handoff.consumer_handoff ?? {};

  return (
    <aside className="lr-handoff-badge" role="note" aria-label="JEMA OS research handoff">
      <div className="lr-handoff-badge__tags">
        <span className="lr-ask-tag">{surface.mode ?? "text_mvp_qa_l0"}</span>
        <span className="lr-ask-tag">{gov.send_gate ?? "HOLD"}</span>
        <span className="lr-ask-tag">
          {surface.live_llm_on_surface ? "LLM-ON" : "LLM-OFF"}
        </span>
        <span className="lr-ask-tag">
          {consumer.mkmlife_inference_runtime_active ? "RUNTIME-ON" : "RUNTIME-OFF"}
        </span>
      </div>
      <p className="lr-handoff-brand">
        {handoff.brand?.public_name ?? "JEMA OS v2"} · {handoff.brand?.product_line_ko ?? "연구 워크스페이스"}
        {surface.graphics_studio_excluded ? " · Studio 그래픽 제외" : ""}
      </p>
      {gov.disclaimer_ko ? <p className="lr-handoff-disclaimer">{gov.disclaimer_ko}</p> : null}
    </aside>
  );
}
