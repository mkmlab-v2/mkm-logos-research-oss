"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

export type PaletteAction = {
  id: string;
  label: string;
  hint?: string;
  run: () => void;
};

type JemaWorkspaceCommandPaletteProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actions: PaletteAction[];
};

export function JemaWorkspaceCommandPalette({ open, onOpenChange, actions }: JemaWorkspaceCommandPaletteProps) {
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return actions;
    return actions.filter((a) => `${a.label} ${a.hint || ""}`.toLowerCase().includes(s));
  }, [actions, q]);

  useEffect(() => {
    if (!open) {
      setQ("");
      setIdx(0);
    }
  }, [open]);

  useEffect(() => {
    setIdx(0);
  }, [q, open]);

  const runActive = useCallback(() => {
    const a = filtered[idx];
    if (!a) return;
    a.run();
    onOpenChange(false);
  }, [filtered, idx, onOpenChange]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onOpenChange(false);
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setIdx((i) => Math.min(i + 1, Math.max(0, filtered.length - 1)));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setIdx((i) => Math.max(0, i - 1));
      }
      if (e.key === "Enter") {
        e.preventDefault();
        runActive();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, filtered.length, runActive, onOpenChange]);

  if (!open) return null;

  return (
    <div className="palette-backdrop" role="presentation" onClick={() => onOpenChange(false)}>
      <div className="palette-dialog" role="dialog" aria-modal="true" aria-label="명령 팔레트" onClick={(e) => e.stopPropagation()}>
        <input
          className="palette-input"
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="이동 또는 실행 검색…"
          aria-autocomplete="list"
        />
        <ul className="palette-list" role="listbox">
          {filtered.map((a, i) => (
            <li key={a.id} role="option" aria-selected={i === idx}>
              <button
                type="button"
                className={`palette-item${i === idx ? " is-active" : ""}`}
                onClick={() => {
                  setIdx(i);
                  a.run();
                  onOpenChange(false);
                }}
              >
                <span>{a.label}</span>
                {a.hint ? <span className="palette-hint">{a.hint}</span> : null}
              </button>
            </li>
          ))}
        </ul>
        <p className="palette-foot">Esc 닫기 · ↑↓ 선택 · Enter 실행</p>
      </div>
    </div>
  );
}
