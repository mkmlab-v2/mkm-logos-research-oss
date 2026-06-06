"use client";

import { useEffect, useState, type ReactNode } from "react";
import { ClinicianPilotDisclaimerFooter } from "@/components/ClinicianPilotDisclaimerFooter";
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

  function handleNewConsult() {
    onNewConsult();
    select("chat");
    setDrawerOpen(false);
  }

  const sidebarInner = (
    <>
      <div className="minimal-clinician-sidebar-head">
        <div className="minimal-clinician-brand minimal-clinician-brand--sidebar" aria-label="서비스">
          JEMA AI
          <span className="minimal-clinician-brand-tag">{roleLabel}</span>
        </div>
        <button type="button" className="minimal-clinician-new-chat" onClick={handleNewConsult}>
          + 새 상담
        </button>
      </div>
      {sidebarBody ? <div className="minimal-clinician-sidebar-threads">{sidebarBody}</div> : null}
      <nav className="minimal-clinician-sidebar-nav" aria-label="워크스페이스 메뉴">
        {nav.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`minimal-clinician-nav-item${activeId === item.id ? " is-active" : ""}`}
            onClick={() => select(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <div className="minimal-clinician-sidebar-foot">
        <a
          className="minimal-clinician-ghost-btn minimal-clinician-hub-link"
          href={JEMA_AI_PUBLIC_ORIGIN}
          target="_blank"
          rel="noopener noreferrer"
        >
          브랜드 허브
        </a>
        <p className="workspace-sidebar-note minimal-clinician-sidebar-note">
          <kbd className="workspace-kbd">Ctrl</kbd>+<kbd className="workspace-kbd">K</kbd> 명령 팔레트
        </p>
      </div>
    </>
  );

  return (
    <div className="minimal-clinician-shell" data-clinician-pilot="v1" data-clinician-sidebar="gpt-persist">
      <a className="skip" href="#minimal-clinician-main">
        본문으로 건너뛰기
      </a>

      <div className="minimal-clinician-layout">
        <aside
          id="minimal-clinician-sidebar"
          className={`minimal-clinician-sidebar${drawerOpen ? " is-mobile-open" : ""}`}
          aria-label="대화 목록 및 메뉴"
        >
          {sidebarInner}
        </aside>

        <div className="minimal-clinician-column">
          <header className="minimal-clinician-topbar minimal-clinician-topbar--mobile">
            <div className="minimal-clinician-topbar-inner">
              <button
                type="button"
                className="minimal-clinician-menu-btn"
                aria-expanded={drawerOpen}
                aria-controls="minimal-clinician-sidebar"
                onClick={() => setDrawerOpen((v) => !v)}
              >
                대화 목록
              </button>
              <button type="button" className="minimal-clinician-ghost-btn" onClick={handleNewConsult}>
                새 상담
              </button>
            </div>
          </header>

          {drawerOpen ? (
            <button
              type="button"
              className="workspace-backdrop minimal-clinician-backdrop"
              aria-label="사이드바 닫기"
              onClick={() => setDrawerOpen(false)}
            />
          ) : null}

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

          <ClinicianPilotDisclaimerFooter onOpenSafety={() => select("safety")} />
        </div>
      </div>
    </div>
  );
}
