"use client";

import { useCallback, useEffect, useState } from "react";
import type { ClinicianChatThread, ClinicianThreadMetaPatch } from "@/lib/clinician-chat-types";
import { threadDisplayPrimary, threadDisplaySecondary } from "@/lib/clinician-chat-storage";

type ClinicianThreadRailProps = {
  threads: ClinicianChatThread[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onUpdateMeta: (id: string, meta: ClinicianThreadMetaPatch) => void;
};

type EditDraft = {
  patientLabel: string;
  title: string;
  sessionDate: string;
};

export function ClinicianThreadRail({
  threads,
  activeId,
  onSelect,
  onDelete,
  onUpdateMeta,
}: ClinicianThreadRailProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [draft, setDraft] = useState<EditDraft>({ patientLabel: "", title: "", sessionDate: "" });

  const sorted = [...threads].sort((a, b) => b.updatedAt - a.updatedAt);

  useEffect(() => {
    if (!menuId) return;
    const close = () => setMenuId(null);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [menuId]);

  const openEdit = useCallback((t: ClinicianChatThread) => {
    setEditingId(t.id);
    setMenuId(null);
    setDraft({
      patientLabel: t.patientLabel?.trim() ?? "",
      title: t.title?.trim() ?? "",
      sessionDate: t.sessionDate?.trim() ?? "",
    });
  }, []);

  const saveEdit = useCallback(
    (id: string) => {
      onUpdateMeta(id, {
        patientLabel: draft.patientLabel.trim(),
        title: draft.title.trim() || "새 상담",
        sessionDate: draft.sessionDate.trim(),
        titlePinned: true,
      });
      setEditingId(null);
    },
    [draft, onUpdateMeta],
  );

  return (
    <div className="thread-rail thread-rail--gpt" role="navigation" aria-label="대화 기록">
      <p className="thread-rail-label">대화 기록</p>
      <ul className="thread-rail-list">
        {sorted.map((t) => {
          const isEditing = editingId === t.id;
          const menuOpen = menuId === t.id;
          return (
            <li
              key={t.id}
              className={`thread-rail-item${t.id === activeId ? " is-active" : ""}${isEditing ? " is-editing" : ""}`}
            >
              {isEditing ? (
                <div className="thread-rail-edit">
                  <label className="thread-rail-edit-label">
                    환자 이름
                    <input
                      type="text"
                      value={draft.patientLabel}
                      onChange={(e) => setDraft((d) => ({ ...d, patientLabel: e.target.value }))}
                      placeholder="예: 홍길동"
                      autoFocus
                    />
                  </label>
                  <label className="thread-rail-edit-label">
                    대화 제목
                    <input
                      type="text"
                      value={draft.title}
                      onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value }))}
                      placeholder="예: 두통·소화 상담"
                    />
                  </label>
                  <label className="thread-rail-edit-label">
                    날짜
                    <input
                      type="date"
                      value={draft.sessionDate}
                      onChange={(e) => setDraft((d) => ({ ...d, sessionDate: e.target.value }))}
                    />
                  </label>
                  <div className="thread-rail-edit-actions">
                    <button type="button" className="thread-rail-edit-save" onClick={() => saveEdit(t.id)}>
                      저장
                    </button>
                    <button type="button" className="thread-rail-edit-cancel" onClick={() => setEditingId(null)}>
                      취소
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <button
                    type="button"
                    className="thread-rail-select"
                    onClick={() => onSelect(t.id)}
                    title={threadDisplayPrimary(t)}
                  >
                    <span className="thread-rail-title">{threadDisplayPrimary(t)}</span>
                    <span className="thread-rail-meta">{threadDisplaySecondary(t)}</span>
                  </button>
                  <div className="thread-rail-actions" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="thread-rail-menu"
                      aria-expanded={menuOpen}
                      aria-label={`${threadDisplayPrimary(t)} 메뉴`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuId((cur) => (cur === t.id ? null : t.id));
                      }}
                    >
                      ⋯
                    </button>
                    {menuOpen ? (
                      <div className="thread-rail-menu-pop" role="menu" onClick={(e) => e.stopPropagation()}>
                        <button type="button" role="menuitem" onClick={() => openEdit(t)}>
                          이름·날짜 편집
                        </button>
                        <button
                          type="button"
                          role="menuitem"
                          className="is-danger"
                          onClick={() => {
                            setMenuId(null);
                            onDelete(t.id);
                          }}
                        >
                          삭제
                        </button>
                      </div>
                    ) : null}
                  </div>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
