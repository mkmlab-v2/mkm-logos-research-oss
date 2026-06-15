"use client";

import { useEffect, useState } from "react";

export function PersonadiaryOfflineNotice() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const sync = () => setOffline(!navigator.onLine);
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, []);

  if (!offline) return null;

  return (
    <p className="pd-ops-offline-banner" role="status">
      오프라인 — 일기·북극성·주간 목표는 이 기기(IndexedDB)에 저장됩니다. 가이드 Pull은 연결이 필요합니다.
    </p>
  );
}
