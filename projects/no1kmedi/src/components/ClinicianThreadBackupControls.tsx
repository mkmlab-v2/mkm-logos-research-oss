"use client";

import { useRef, useState } from "react";

import type { ClinicianChatThread } from "@/lib/clinician-chat-types";
import {
  downloadClinicianThreadsBackup,
  mergeImportedClinicianThreads,
  parseClinicianThreadsBackup,
  saveClinicianThreads,
} from "@/lib/clinician-chat-storage";

type ClinicianThreadBackupControlsProps = {
  threads: ClinicianChatThread[];
  onThreadsImported: (threads: ClinicianChatThread[]) => void;
};

export function ClinicianThreadBackupControls({
  threads,
  onThreadsImported,
}: ClinicianThreadBackupControlsProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<string | null>(null);

  function handleExport() {
    downloadClinicianThreadsBackup(threads);
    setStatus("대화 기록 JSON을 보냈습니다.");
    window.setTimeout(() => setStatus(null), 3000);
  }

  async function handleImport(file: File) {
    try {
      const raw = await file.text();
      const parsed = parseClinicianThreadsBackup(raw);
      if (!parsed.ok) {
        setStatus(`가져오기 실패: ${parsed.error}`);
        return;
      }
      const merged = mergeImportedClinicianThreads(threads, parsed.threads);
      saveClinicianThreads(merged);
      onThreadsImported(merged);
      setStatus(`대화 ${parsed.threads.length}건 병합 · 총 ${merged.length}건`);
      window.setTimeout(() => setStatus(null), 4000);
    } catch {
      setStatus("파일을 읽지 못했습니다.");
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="thread-backup-controls" aria-label="대화 기록 백업">
      <p className="thread-backup-label">로컬 백업 (P0.5)</p>
      <div className="thread-backup-actions">
        <button type="button" className="thread-backup-btn" onClick={handleExport}>
         보내기
        </button>
        <button type="button" className="thread-backup-btn" onClick={() => inputRef.current?.click()}>
          가져오기
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/json,.json"
          className="sr-only"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleImport(file);
          }}
        />
      </div>
      {status ? <p className="thread-backup-status">{status}</p> : null}
      <p className="thread-backup-hint">브라우저 캐시 삭제 전 JSON으로 보관하세요. 이 PC에만 저장됩니다.</p>
    </div>
  );
}
