"use client";

import { useMemo, useState } from "react";
import { initializePaddle } from "@paddle/paddle-js";

type PaddleEnv = "sandbox" | "production";

function getPaddleEnv(value: string | undefined): PaddleEnv {
  return value?.toLowerCase() === "live" ? "production" : "sandbox";
}

export function PaddleCheckoutButton() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string>("");

  const clientToken = process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN;
  const priceId = process.env.NEXT_PUBLIC_PADDLE_PRICE_ID;
  const env = useMemo(() => getPaddleEnv(process.env.NEXT_PUBLIC_PADDLE_ENV), []);

  async function handleCheckout() {
    if (!clientToken || !priceId) {
      setMessage("Paddle env가 비어 있습니다. NEXT_PUBLIC_PADDLE_CLIENT_TOKEN / NEXT_PUBLIC_PADDLE_PRICE_ID를 설정하세요.");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const paddle = await initializePaddle({
        token: clientToken,
        environment: env,
      });

      if (!paddle) {
        setMessage("Paddle 초기화에 실패했습니다.");
        return;
      }

      paddle.Checkout.open({
        items: [{ priceId, quantity: 1 }],
      });
    } catch (error) {
      const msg = error instanceof Error ? error.message : "unknown_error";
      setMessage(`Paddle checkout 오류: ${msg}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: "0.5rem" }}>
      <button
        type="button"
        className="btn btn-ghost"
        onClick={handleCheckout}
        disabled={loading}
      >
        {loading ? "Paddle 로딩 중..." : "Paddle Checkout 테스트"}
      </button>
      {message ? (
        <p className="trust-note" role="status">
          {message}
        </p>
      ) : null}
    </div>
  );
}

