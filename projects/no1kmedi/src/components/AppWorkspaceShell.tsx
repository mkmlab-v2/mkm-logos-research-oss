"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";

export type WorkspaceNavItem = { id: string; label: string };

type AppWorkspaceShellProps = {
  homeHref?: string;
  roleLabel: string;
  nav: WorkspaceNavItem[];
  activeId: string;
  onSelect: (id: string) => void;
  /** 네비 아래 (예: 대화 스레드 목록) */
  sidebarBody?: ReactNode;
  /** 사이드바 본문 아래 · 안내 문구 위 (예: 새 대화) */
  sidebarFooter?: ReactNode;
  children: ReactNode;
};

export function AppWorkspaceShell({
  homeHref = "/",
  roleLabel,
  nav,
  activeId,
  onSelect,
  sidebarBody,
  sidebarFooter,
  children,
}: AppWorkspaceShellProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileNavOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileNavOpen]);

  function select(id: string) {
    onSelect(id);
    setMobileNavOpen(false);
  }

  return (
    <div className="app-workspace">
      <a className="skip" href="#workspace-main">
        본문으로 건너뛰기
      </a>
      <header className="workspace-topbar">
        <div className="workspace-topbar-inner">
          <button
            type="button"
            className="workspace-nav-toggle"
            aria-expanded={mobileNavOpen}
            aria-controls="workspace-sidebar"
            onClick={() => setMobileNavOpen((v) => !v)}
          >
            메뉴
          </button>
          <Link className="workspace-brand" href={homeHref}>
            JEMA AI
            <span className="workspace-brand-tag">{roleLabel}</span>
          </Link>
          <Link className="workspace-home-link" href={homeHref}>
            랜딩으로
          </Link>
        </div>
      </header>

      {mobileNavOpen ? (
        <button
          type="button"
          className="workspace-backdrop"
          aria-label="메뉴 닫기"
          onClick={() => setMobileNavOpen(false)}
        />
      ) : null}

      <div className="workspace-body">
        <aside
          className={`workspace-sidebar${mobileNavOpen ? " is-open" : ""}`}
          id="workspace-sidebar"
          aria-label="작업 메뉴"
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
          {sidebarFooter ? <div className="workspace-sidebar-actions">{sidebarFooter}</div> : null}
          <p className="workspace-sidebar-note">
            메뉴는 이후 설문·기록·도입 문의 등으로 확장할 수 있도록 분리해 두었습니다. 전역 명령:{" "}
            <kbd className="workspace-kbd">Ctrl</kbd>+<kbd className="workspace-kbd">K</kbd> 또는{" "}
            <kbd className="workspace-kbd">⌘</kbd>+<kbd className="workspace-kbd">K</kbd>.
          </p>
        </aside>

        <main id="workspace-main" className="workspace-main">
          {children}
        </main>
      </div>
    </div>
  );
}
