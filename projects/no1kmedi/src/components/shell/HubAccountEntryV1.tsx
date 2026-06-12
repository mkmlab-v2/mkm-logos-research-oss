"use client";

import { useState } from "react";
import { useMkmFamilySessionV1 } from "@/hooks/useMkmFamilySessionV1";

type Props = {
  compact?: boolean;
};

export function HubAccountEntryV1({ compact = false }: Props) {
  const { session, loading, refresh } = useMkmFamilySessionV1();
  const [busy, setBusy] = useState(false);

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

  if (loading || !session) {
    return compact ? null : (
      <div className="universe-hub-account-entry" aria-busy={loading}>
        {loading ? <span className="universe-hub-account-muted">MKM 계정 확인 중…</span> : null}
      </div>
    );
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
