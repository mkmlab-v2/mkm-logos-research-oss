"use client";

import { useCallback, useEffect, useState } from "react";

type SessionResponse = {
  ok: boolean;
  configured: boolean;
  authenticated: boolean;
  account?: {
    mkm_account_id: string;
    email: string;
    display_name?: string;
    picture_url?: string;
  };
};

type Props = {
  compact?: boolean;
};

export function HubAccountEntryV1({ compact = false }: Props) {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/mkm-family/session", { credentials: "include" });
      const data = (await res.json()) as SessionResponse;
      setSession(data);
    } catch {
      setSession({ ok: false, configured: false, authenticated: false });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onGoogleLogin = () => {
    window.location.href = `/api/mkm-family/auth/google?return_to=${encodeURIComponent("/hub")}`;
  };

  const onLogout = async () => {
    setBusy(true);
    try {
      await fetch("/api/mkm-family/logout", { method: "POST", credentials: "include" });
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const openRp = (product: "mkmlife" | "personadiary") => {
    window.location.href = `/api/mkm-family/rp/handoff?product=${product}`;
  };

  if (!session) {
    return compact ? null : <div className="universe-hub-account-entry" aria-busy="true" />;
  }

  if (!session.configured) {
    return (
      <div className={`universe-hub-account-entry${compact ? " is-compact" : ""}`}>
        <span className="universe-hub-account-muted" title="OAuth env 미설정">
          MKM 계정 · 준비 중
        </span>
      </div>
    );
  }

  if (!session.authenticated || !session.account) {
    return (
      <div className={`universe-hub-account-entry${compact ? " is-compact" : ""}`}>
        <button
          type="button"
          className="universe-hub-account-google-btn"
          onClick={onGoogleLogin}
          disabled={busy}
        >
          Google로 시작
        </button>
      </div>
    );
  }

  const label = session.account.display_name || session.account.email.split("@")[0];

  return (
    <div className={`universe-hub-account-entry${compact ? " is-compact" : ""}`}>
      <div className="universe-hub-account-user" title={session.account.email}>
        {session.account.picture_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            className="universe-hub-account-avatar"
            src={session.account.picture_url}
            alt=""
            width={24}
            height={24}
          />
        ) : null}
        <span className="universe-hub-account-label">{label}</span>
      </div>
      {!compact ? (
        <div className="universe-hub-account-rp-row">
          <button type="button" className="universe-hub-account-rp-btn" onClick={() => openRp("mkmlife")}>
            mkmlife 연결
          </button>
          <button type="button" className="universe-hub-account-rp-btn" onClick={() => openRp("personadiary")}>
            Diary 연결
          </button>
          <button type="button" className="universe-hub-account-logout" onClick={onLogout} disabled={busy}>
            로그아웃
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="universe-hub-account-logout is-compact"
          onClick={onLogout}
          disabled={busy}
          aria-label="로그아웃"
        >
          ⎋
        </button>
      )}
    </div>
  );
}
