"use client";

import { useState } from "react";

import { LogosGraphStudioHeroInlineDemo } from "@/components/logos/LogosGraphStudioHeroInlineDemo";

type Props = {
  title: string;
  lead: string;
  presetId?: string;
};

/**
 * User-initiated Graph Studio demo fold.
 *
 * B2B demo UX evidence (Chameleon, 550M interactions): auto-triggered tours complete
 * at ~31% vs ~67% for user-initiated. So the on-domain Layer-B inline demo is mounted
 * only when the user opens this <details> fold — never auto-played on page load — and
 * the underlying demo still respects prefers-reduced-motion. Keeps the home hero
 * text-Q&A-first while shipping the real (previously orphaned) Layer-B storyboard UX.
 */
export function LogosResearchStudioDemoFold({ title, lead, presetId }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <details
      className="lr-section lr-studio-deferred"
      data-logos-studio-demo-fold="1"
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary>
        <span className="lr-studio-deferred-badge">{title}</span>
      </summary>
      <p className="lr-section-lead">{lead}</p>
      {open ? (
        <LogosGraphStudioHeroInlineDemo
          presetId={presetId}
          className="lr-studio-deferred-demo"
          note="30초 스토리보드 · 펼쳤을 때만 재생 · citation-locked · [HYPO] NON_GATING"
        />
      ) : null}
      <p className="lr-studio-deferred-actions">
        <a className="lr-btn lr-btn-ghost" href="/logos-research/studio">
          Studio 미리보기 (연구용)
        </a>
      </p>
    </details>
  );
}
