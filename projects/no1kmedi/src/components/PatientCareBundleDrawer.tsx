"use client";

import { useEffect, type ReactNode } from "react";

type PatientCareBundleDrawerProps = {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
};

export function PatientCareBundleDrawer({ open, onClose, children }: PatientCareBundleDrawerProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <aside
      className={`clinical-bundle-drawer${open ? " is-open" : ""}`}
      aria-hidden={!open}
      aria-label="CDSS 환자 번들"
    >
      {open ? (
        <button type="button" className="clinical-bundle-drawer-backdrop" aria-label="닫기" onClick={onClose} />
      ) : null}
      <div className="clinical-bundle-drawer-panel">
        <header className="clinical-bundle-drawer-header">
          <div>
            <p className="clinical-bundle-drawer-eyebrow">Track B · 보조</p>
            <h2 className="clinical-bundle-drawer-title">CDSS · 환자 번들</h2>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            닫기
          </button>
        </header>
        <div className="clinical-bundle-drawer-body">{children}</div>
        <p className="clinical-bundle-drawer-foot">
          원장 수동 확인 전 · 차트·EMR 미연동 · [HYPO] 참고용
        </p>
      </div>
    </aside>
  );
}
