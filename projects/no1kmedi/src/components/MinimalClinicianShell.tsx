"use client";

import { useEffect, useState, type ReactNode } from "react";
import { JEMA_AI_PUBLIC_ORIGIN } from "@/lib/no1kmedi-portal-host";
import type { WorkspaceNavItem } from "@/components/AppWorkspaceShell";

type MinimalClinicianShellProps = {
  roleLabel: string;
  nav: WorkspaceNavItem[];
  activeId: string;
  onSelect: (id: string) => void;
  sidebarBody?: ReactNode;
  onNewConsult: () => void;
  children: ReactNode;
};

export function MinimalClinicianShell({
  roleLabel,
  nav,
  activeId,
  onSelect,
  sidebarBody,
  onNewConsult,
  children,
}: MinimalClinicianShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  function select(id: string) {
    onSelect(id);
    setDrawerOpen(false);
  }

  return (
    <div className="minimal-clinician-shell">
      <a className="skip" href="#minimal-clinician-main">
        본문으로 건너뛰기
      </a>
      <header className="minimal-clinician-topbar">
        <div className="minimal-clinician-topbar-inner">
          <button
            type="button"
            className="minimal-clinician-menu-btn"
            aria-expanded={drawerOpen}
            aria-controls="minimal-clinician-drawer"
            onClick={() => setDrawerOpen((v) => !v)}
          >
            대화·메뉴
          </button>
          <div className="minimal-clinician-brand" aria-label="서비스">
            JEMA AI
            <span className="minimal-clinician-brand-tag">{roleLabel}</span>
          </div>
          <div className="minimal-clinician-topbar-actions">
            <button type="button" className="minimal-clinician-ghost-btn" onClick={onNewConsult}>
              새 상담
            </button>
            <a
              className="minimal-clinician-ghost-btn minimal-clinician-hub-link"
              href={JEMA_AI_PUBLIC_ORIGIN}
              target="_blank"
              rel="noopener noreferrer"
            >
              브랜드 허브
            </a>
          </div>
        </div>
      </header>

      {drawerOpen ? (
        <button
          type="button"
          className="workspace-backdrop"
          aria-label="메뉴 닫기"
          onClick={() => setDrawerOpen(false)}
        />
      ) : null}

      <aside
        id="minimal-clinician-drawer"
        className={`minimal-clinician-drawer${drawerOpen ? " is-open" : ""}`}
        aria-label="대화 목록 및 설정"
        aria-hidden={!drawerOpen}
      >
        <nav className="workspace-nav">
          {nav.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`workspace-nav-item${activeId === item.id ? " is-active" : ""}`}
              onClick={() => select(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        {sidebarBody ? <div className="workspace-sidebar-body">{sidebarBody}</div> : null}
        <div className="workspace-sidebar-actions">
          <button type="button" className="workspace-secondary-btn" onClick={() => select("chat")}>
            대화로 돌아가기
          </button>
        </div>
        <p className="workspace-sidebar-note">
          명령 팔레트: <kbd className="workspace-kbd">Ctrl</kbd>+<kbd className="workspace-kbd">K</kbd> 또는{" "}
          <kbd className="workspace-kbd">⌘</kbd>+<kbd className="workspace-kbd">K</kbd>
        </p>
      </aside>

      <main
        id="minimal-clinician-main"
        className={`minimal-clinician-main${activeId !== "chat" ? " minimal-clinician-main--panel" : ""}`}
      >
        {activeId !== "chat" ? (
          <button type="button" className="minimal-clinician-back-btn" onClick={() => select("chat")}>
            ← 대화로
          </button>
        ) : null}
        {children}
      </main>
    </div>
  );
}
