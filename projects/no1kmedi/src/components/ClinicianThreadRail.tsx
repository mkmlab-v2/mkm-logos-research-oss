"use client";

import type { ClinicianChatThread } from "@/lib/clinician-chat-types";

type ClinicianThreadRailProps = {
  threads: ClinicianChatThread[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
};

export function ClinicianThreadRail({ threads, activeId, onSelect, onDelete }: ClinicianThreadRailProps) {
  const sorted = [...threads].sort((a, b) => b.updatedAt - a.updatedAt);

  return (
    <div className="thread-rail" role="navigation" aria-label="상담 기록">
      <p className="thread-rail-label">상담 기록</p>
      <ul className="thread-rail-list">
        {sorted.map((t) => (
          <li key={t.id} className={`thread-rail-item${t.id === activeId ? " is-active" : ""}`}>
            <button type="button" className="thread-rail-select" onClick={() => onSelect(t.id)} title={t.title}>
              <span className="thread-rail-title">{t.title}</span>
              <span className="thread-rail-meta">
                {new Date(t.updatedAt).toLocaleString("ko-KR", {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </button>
            <button
              type="button"
              className="thread-rail-delete"
              aria-label={`${t.title} 삭제`}
              onClick={(e) => {
                e.stopPropagation();
                onDelete(t.id);
              }}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
