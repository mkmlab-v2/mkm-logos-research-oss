"use client";

import { useCallback, useEffect, useState } from "react";

export type MkmFamilySessionV1 = {
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

export function useMkmFamilySessionV1() {
  const [session, setSession] = useState<MkmFamilySessionV1 | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/mkm-family/session", { credentials: "include" });
      const data = (await res.json()) as MkmFamilySessionV1;
      setSession(data);
    } catch {
      setSession({ ok: false, configured: false, authenticated: false });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { session, loading, refresh };
}
