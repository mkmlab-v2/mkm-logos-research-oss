"use client";

import { useEffect, useRef, useState } from "react";
import { getTurnstileSitekey } from "@/lib/turnstileConfigV1";

type TurnstileFieldProps = {
  onToken: (token: string) => void;
  onExpire?: () => void;
  onError?: () => void;
};

declare global {
  interface Window {
    turnstile?: {
      render: (el: HTMLElement, opts: Record<string, unknown>) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
    };
  }
}

const SCRIPT_ID = "cf-turnstile-script";
const SCRIPT_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

function loadTurnstileScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.turnstile) {
      resolve();
      return;
    }
    const existing = document.getElementById(SCRIPT_ID);
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("turnstile_script_load_failed")), {
        once: true,
      });
      return;
    }
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("turnstile_script_load_failed"));
    document.head.appendChild(script);
  });
}

export function TurnstileField({ onToken, onExpire, onError }: TurnstileFieldProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const onTokenRef = useRef(onToken);
  const onExpireRef = useRef(onExpire);
  const onErrorRef = useRef(onError);
  const [loadError, setLoadError] = useState("");
  const sitekey = getTurnstileSitekey();

  useEffect(() => {
    onTokenRef.current = onToken;
    onExpireRef.current = onExpire;
    onErrorRef.current = onError;
  });

  useEffect(() => {
    if (!sitekey) return;

    let cancelled = false;

    void (async () => {
      try {
        await loadTurnstileScript();
        if (cancelled || !containerRef.current || !window.turnstile) return;
        if (widgetIdRef.current) {
          window.turnstile.remove(widgetIdRef.current);
          widgetIdRef.current = null;
        }
        widgetIdRef.current = window.turnstile.render(containerRef.current, {
          sitekey,
          callback: (token: string) => onTokenRef.current(token),
          "expired-callback": () => onExpireRef.current?.(),
          "error-callback": () => {
            onErrorRef.current?.();
            onExpireRef.current?.();
          },
        });
      } catch {
        if (!cancelled) {
          setLoadError("보안 확인을 불러오지 못했습니다. 새로고침 후 다시 시도해 주세요.");
        }
      }
    })();

    return () => {
      cancelled = true;
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [sitekey]);

  if (!sitekey) return null;

  return (
    <div className="enterprise-apply-turnstile" aria-label="보안 확인">
      <div ref={containerRef} />
      {loadError ? <p className="consult-error">{loadError}</p> : null}
    </div>
  );
}
