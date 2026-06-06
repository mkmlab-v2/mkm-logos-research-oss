"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";

type ClinicianChatFirstShellProps = {
  contextChip: ReactNode;
  onOpenSettings: () => void;
  sidebarBody?: ReactNode;
  sidebarFooter?: ReactNode;
  drawer: ReactNode;
  drawerOpen: boolean;
  onDrawerClose: () => void;
  children: ReactNode;
};

export function ClinicianChatFirstShell({
  contextChip,
  onOpenSettings,
  sidebarBody,
  sidebarFooter,
  drawer,
  drawerOpen,
  onDrawerClose,
  children,
}: ClinicianChatFirstShellProps) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  useEffect(() => {
    if (!mobileSidebarOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileSidebarOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileSidebarOpen]);

  return (
    <div className={`clinician-chat-first${drawerOpen ? " drawer-open" : ""}`}>
      <a className="skip" href="#workspace-main">
        본문으로 건너뛰기
      </a>

      <header className="clinician-chat-first-topbar">
        <div className="clinician-chat-first-topbar-inner">
          <button
            type="button"
            className="workspace-nav-toggle"
            aria-expanded={mobileSidebarOpen}
            aria-controls="clinician-history-sidebar"
            onClick={() => setMobileSidebarOpen((v) => !v)}
          >
            메뉴
          </button>
          <Link className="clinician-chat-first-brand" href="/clinician">
            JEMA AI
            <span className="clinician-chat-first-brand-tag">진료 보조</span>
          </Link>
          <div className="clinician-chat-first-topbar-center">{contextChip}</div>
          <div className="clinician-chat-first-topbar-actions">
            <button
              type="button"
              className="btn btn-ghost btn-sm clinician-topbar-settings"
              aria-label="환자·권한 설정"
              onClick={onOpenSettings}
            >
              ⚙️
            </button>
          </div>
        </div>
      </header>

      {mobileSidebarOpen ? (
        <button
          type="button"
          className="workspace-backdrop"
          aria-label="히스토리 닫기"
          onClick={() => setMobileSidebarOpen(false)}
        />
      ) : null}

      <div className="clinician-chat-first-body">
        <aside
          id="clinician-history-sidebar"
          className={`clinician-chat-first-sidebar${mobileSidebarOpen ? " is-open" : ""}`}
          aria-label="진료 세션 히스토리"
        >
          {sidebarFooter ? (
            <div className="clinician-chat-first-sidebar-new">{sidebarFooter}</div>
          ) : null}
          {sidebarBody ? <div className="clinician-chat-first-sidebar-history">{sidebarBody}</div> : null}
          <p className="clinician-chat-first-sidebar-note">
            <kbd className="workspace-kbd">Ctrl</kbd>+<kbd className="workspace-kbd">K</kbd> 명령
          </p>
        </aside>

        <main id="workspace-main" className="clinician-chat-first-main">
          {children}
        </main>

        {drawer}
      </div>

      {drawerOpen ? (
        <button
          type="button"
          className="clinical-bundle-drawer-backdrop clinical-bundle-drawer-backdrop--mobile-only"
          aria-label="번들 패널 닫기"
          onClick={onDrawerClose}
        />
      ) : null}
    </div>
  );
}
