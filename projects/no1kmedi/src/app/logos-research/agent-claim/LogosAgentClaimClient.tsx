"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

export function LogosAgentClaimClient() {
  const search = useSearchParams();
  const claimAttemptToken = search.get("claim_attempt_token") || "";
  const [email, setEmail] = useState("");
  const [userCode, setUserCode] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [message, setMessage] = useState("");

  const disabled = useMemo(
    () => !claimAttemptToken || !email.trim() || !userCode.trim(),
    [claimAttemptToken, email, userCode],
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setMessage("");
    try {
      const res = await fetch("/api/agent/identity/claim/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_attempt_token: claimAttemptToken,
          user_code: userCode.trim(),
          email: email.trim(),
        }),
      });
      const data = (await res.json()) as { error?: string; ok?: boolean };
      if (!res.ok) {
        setStatus("error");
        setMessage(data.error || `HTTP ${res.status}`);
        return;
      }
      setStatus("ok");
      setMessage("에이전트 연결이 확인되었습니다. 에이전트 창으로 돌아가 주세요.");
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "unknown_error");
    }
  }

  return (
    <main className="mkm-section" style={{ maxWidth: 560, margin: "0 auto", padding: "2rem 1rem" }}>
      <p
        style={{
          fontSize: "var(--text-sm)",
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          color: "var(--muted)",
          marginBottom: "0.35rem",
        }}
      >
        Logos Scripture Research · Institution Pilot
      </p>
      <h1 style={{ fontSize: "var(--text-xl)", marginBottom: "0.5rem" }}>
        에이전트 API 연결 승인
      </h1>
      <p style={{ color: "var(--muted)", marginBottom: "1rem", lineHeight: 1.6 }}>
        연구 보조 에이전트가 귀하의 <strong>기관 이메일</strong>로 Logos API에 접근하려 합니다.
        에이전트 화면의 <strong>6자리 코드</strong>를 아래에 입력해 1회 승인해 주세요.
      </p>
      <p
        style={{
          fontSize: "var(--text-sm)",
          padding: "0.75rem 1rem",
          background: "var(--surface-muted, #f4f6f8)",
          borderRadius: 8,
          border: "1px solid var(--line)",
          marginBottom: "1.25rem",
          lineHeight: 1.5,
        }}
      >
        research_only · send_gate HOLD · 교리·투자·실매매 판단 아님 · 최종 검토는 기관 담당자
      </p>

      {!claimAttemptToken ? (
        <p role="alert">유효하지 않은 링크입니다. 에이전트에게 새 claim 링크를 요청하세요.</p>
      ) : (
        <form onSubmit={onSubmit} style={{ display: "grid", gap: "1rem" }}>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span>기관 이메일</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              style={{ padding: "0.65rem 0.75rem", border: "1px solid var(--line)", borderRadius: 8 }}
            />
          </label>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span>에이전트가 표시한 코드 (6자리)</span>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={userCode}
              onChange={(e) => setUserCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              style={{ padding: "0.65rem 0.75rem", border: "1px solid var(--line)", borderRadius: 8 }}
            />
          </label>
          <button
            type="submit"
            disabled={disabled || status === "loading"}
            style={{
              padding: "0.75rem 1rem",
              borderRadius: 8,
              border: "none",
              background: "var(--accent, #1e3a5f)",
              color: "#fff",
              cursor: disabled ? "not-allowed" : "pointer",
              opacity: disabled ? 0.6 : 1,
            }}
          >
            {status === "loading" ? "확인 중…" : "에이전트 연결 승인"}
          </button>
        </form>
      )}

      {message ? (
        <p
          role="status"
          style={{
            marginTop: "1.25rem",
            color: status === "error" ? "#b42318" : "#027a48",
          }}
        >
          {message}
        </p>
      ) : null}
    </main>
  );
}
