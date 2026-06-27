"use client";

import type { ReactNode } from "react";

export type MkmTrustCanvasScopeBanner = {
  label: string;
  detail?: string;
  tags?: string[];
};

type MkmTrustCanvasShellProps = {
  domainId: string;
  scope: MkmTrustCanvasScopeBanner;
  chat: ReactNode;
  canvas: ReactNode;
  thinking?: ReactNode;
  evidence?: ReactNode;
  /** 우하단 플로팅 Citation Lock (canvas main 기준) */
  citationDock?: ReactNode;
  headerActions?: ReactNode;
  className?: string;
};

export function MkmTrustCanvasShell({
  domainId,
  scope,
  chat,
  canvas,
  thinking,
  evidence,
  citationDock,
  headerActions,
  className,
}: MkmTrustCanvasShellProps) {
  return (
    <div
      className={`mkm-trust-canvas${className ? ` ${className}` : ""}`}
      data-mkm-trust-canvas="1"
      data-mkm-trust-canvas-domain={domainId}
    >
      <header className="mkm-trust-canvas-scope" aria-label="연구 범위">
        <div className="mkm-trust-canvas-scope-text">
          <span className="mkm-trust-canvas-scope-label">{scope.label}</span>
          {scope.detail ? (
            <span className="mkm-trust-canvas-scope-detail">{scope.detail}</span>
          ) : null}
        </div>
        {scope.tags?.length ? (
          <ul className="mkm-trust-canvas-scope-tags" aria-label="범위 태그">
            {scope.tags.map((tag) => (
              <li key={tag} data-tag-hold={/send_gate|HOLD/i.test(tag) ? "1" : undefined}>
                {tag}
              </li>
            ))}
          </ul>
        ) : null}
        {headerActions ? (
          <div className="mkm-trust-canvas-scope-actions">{headerActions}</div>
        ) : null}
      </header>

      <div className="mkm-trust-canvas-body">
        <aside className="mkm-trust-canvas-chat" aria-label="질의">
          {chat}
        </aside>
        <section className="mkm-trust-canvas-main" aria-label="캔버스">
          {thinking ? (
            <div className="mkm-trust-canvas-thinking" aria-label="경로 조립">
              {thinking}
            </div>
          ) : null}
          <div className="mkm-trust-canvas-canvas">{canvas}</div>
          {citationDock ? (
            <div
              className="mkm-trust-canvas-citation-dock"
              aria-label="인용 잠금"
              data-mkm-trust-canvas-citation-dock="1"
            >
              {citationDock}
            </div>
          ) : null}
          {evidence ? (
            <div className="mkm-trust-canvas-evidence" aria-label="증거 패널">
              {evidence}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
