"use client";

import { useMemo, useState } from "react";
import { initializePaddle } from "@paddle/paddle-js";
import { siteCopy } from "@/content/siteCopy";

type PaddleEnv = "sandbox" | "production";

function getPaddleEnv(value: string | undefined): PaddleEnv {
  return value?.toLowerCase() === "live" ? "production" : "sandbox";
}

export function PaddleCheckoutButton() {
  const copy = siteCopy.paddle_checkout;
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string>("");

  const clientToken = process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN;
  const priceId = process.env.NEXT_PUBLIC_PADDLE_PRICE_ID;
  const env = useMemo(() => getPaddleEnv(process.env.NEXT_PUBLIC_PADDLE_ENV), []);

  async function handleCheckout() {
    if (!clientToken || !priceId) {
      setMessage(copy.errors.missing_env);
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
        setMessage(copy.errors.init_failed);
        return;
      }

      paddle.Checkout.open({
        items: [{ priceId, quantity: 1 }],
      });
    } catch (error) {
      const msg = error instanceof Error ? error.message : "unknown_error";
      setMessage(`${copy.errors.checkout_prefix}${msg}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="paddle-checkout-root">
      <button type="button" className="btn btn-ghost" onClick={handleCheckout} disabled={loading}>
        {loading ? copy.button_loading : copy.button_idle}
      </button>
      {clientToken && priceId ? (
        <p className="trust-note paddle-checkout-hint">{copy.hint}</p>
      ) : null}
      {message ? (
        <p className="trust-note" role="status">
          {message}
        </p>
      ) : null}
    </div>
  );
}
