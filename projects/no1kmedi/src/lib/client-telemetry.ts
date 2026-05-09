"use client";

type EventPayload = Record<string, unknown> & { event: string };

function getSessionId() {
  if (typeof window === "undefined") return "ssr";
  const KEY = "mkm_client_session_id_v1";
  try {
    const existing = window.sessionStorage.getItem(KEY);
    if (existing && existing.trim()) return existing;
    const next = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    window.sessionStorage.setItem(KEY, next);
    return next;
  } catch {
    return `sess_fallback_${Date.now()}`;
  }
}

function pushDataLayer(payload: EventPayload) {
  if (typeof window === "undefined") return;
  const w = window as Window & { dataLayer?: Array<Record<string, unknown>> };
  if (Array.isArray(w.dataLayer)) {
    w.dataLayer.push(payload);
  }
}

function postTelemetry(payload: EventPayload) {
  if (typeof window === "undefined") return;
  const body = JSON.stringify(payload);
  try {
    if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
      const blob = new Blob([body], { type: "application/json" });
      navigator.sendBeacon("/api/telemetry/event", blob);
      return;
    }
  } catch {
    // noop fallback
  }
  fetch("/api/telemetry/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => undefined);
}

export function trackClientEvent(event: string, payload?: Record<string, unknown>) {
  const row: EventPayload = {
    event,
    session_id: getSessionId(),
    page_path: typeof window !== "undefined" ? window.location.pathname : "",
    ...(payload || {}),
  };
  pushDataLayer(row);
  postTelemetry(row);
}
