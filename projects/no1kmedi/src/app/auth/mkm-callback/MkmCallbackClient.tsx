"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

type ExchangeResponse = {
  ok: boolean;
  error?: string;
  mkm_account_id?: string;
  product?: string;
  product_profile_id?: string;
};

const STORAGE_KEY = "mkm_family_account_id";
const PROFILE_KEY = "mkm_family_product_profile_id";

export function MkmCallbackClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [message, setMessage] = useState("MKM Family 계정 연결 중…");

  useEffect(() => {
    const code = searchParams.get("mkm_handoff");
    if (!code) {
      setMessage("handoff 코드가 없습니다.");
      return;
    }

    (async () => {
      try {
        const res = await fetch("/api/mkm-family/rp/exchange", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        });
        const data = (await res.json()) as ExchangeResponse;
        if (!data.ok || !data.mkm_account_id) {
          setMessage(data.error || "연결 실패");
          return;
        }

        sessionStorage.setItem(STORAGE_KEY, data.mkm_account_id);
        if (data.product_profile_id) {
          sessionStorage.setItem(PROFILE_KEY, data.product_profile_id);
        }

        if (data.product === "personadiary") {
          router.replace("/personadiary");
          return;
        }
        router.replace("/hub");
      } catch {
        setMessage("네트워크 오류");
      }
    })();
  }, [searchParams, router]);

  return (
    <>
      <h1>MKM Family</h1>
      <p>{message}</p>
      <p className="universe-hub-account-muted">federation_only · DB 합선 없음</p>
    </>
  );
}
