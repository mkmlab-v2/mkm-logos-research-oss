"use client";

import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function isIosSafari(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  const isIos = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
  return isIos && isSafari;
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

export function PersonadiaryPwaInstallBanner() {
  const [hidden, setHidden] = useState(true);
  const [mode, setMode] = useState<"ios" | "android" | null>(null);
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    if (isStandalone()) return;
    if (typeof window !== "undefined" && sessionStorage.getItem("pd_pwa_install_dismissed") === "1") {
      return;
    }
    if (isIosSafari()) {
      setMode("ios");
      setHidden(false);
      return;
    }
    const onBip = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      setMode("android");
      setHidden(false);
    };
    window.addEventListener("beforeinstallprompt", onBip);
    return () => window.removeEventListener("beforeinstallprompt", onBip);
  }, []);

  function dismiss() {
    sessionStorage.setItem("pd_pwa_install_dismissed", "1");
    setHidden(true);
  }

  async function installAndroid() {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setHidden(true);
  }

  if (hidden || !mode) return null;

  return (
    <section className="pd-ops-pwa-install pd-pwa-install" aria-label="앱 설치 안내">
      <div className="pd-ops-pwa-install-inner">
        {mode === "ios" ? (
          <>
            <p className="pd-ops-pwa-install-title">iPhone에 추가</p>
            <p className="pd-ops-pwa-install-copy">
              Safari <strong>공유</strong> → <strong>홈 화면에 추가</strong> — 일기·북극성은 이 기기에만
              저장됩니다.
            </p>
          </>
        ) : (
          <>
            <p className="pd-ops-pwa-install-title">홈 화면에 설치</p>
            <p className="pd-ops-pwa-install-copy">
              앱처럼 열기 · 푸시 없음 · 서버 일기 업로드 없음
            </p>
            <button type="button" className="pd-ops-pwa-install-btn" onClick={() => void installAndroid()}>
              설치
            </button>
          </>
        )}
        <button type="button" className="pd-ops-pwa-install-dismiss" onClick={dismiss} aria-label="닫기">
          ×
        </button>
      </div>
    </section>
  );
}
