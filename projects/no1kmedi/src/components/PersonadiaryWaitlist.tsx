"use client";

import { useState } from "react";
import { personadiaryCopy } from "@/content/personadiaryCopy";

type WaitlistApiResponse = {
  success: boolean;
  lead_id?: string;
  error?: string;
};

function PersonadiaryWaitlistForm() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim() || !email.includes("@")) {
      setError("유효한 이메일을 입력해 주세요.");
      return;
    }
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const res = await fetch("/api/leads/personadiary-waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          name: name.trim(),
          note: note.trim(),
        }),
      });
      const json = (await res.json()) as WaitlistApiResponse;
      if (!res.ok || !json.success) {
        setError(json.error || "등록 중 오류가 발생했습니다.");
        return;
      }
      setStatus("사전 알림 등록이 완료되었습니다. 출시 소식을 이메일로 안내드립니다.");
      setEmail("");
      setName("");
      setNote("");
    } catch {
      setError("네트워크 오류입니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="pd-waitlist-form" onSubmit={onSubmit}>
      <label className="pd-waitlist-field">
        <span>이메일 (필수)</span>
        <input
          type="email"
          name="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
      </label>
      <label className="pd-waitlist-field">
        <span>이름 (선택)</span>
        <input
          type="text"
          name="name"
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className="pd-waitlist-field">
        <span>한 줄 메모 (선택)</span>
        <textarea
          name="note"
          rows={2}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="관심 이유를 적어 주세요 (선택)"
        />
      </label>
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? "등록 중…" : "사전 알림 등록"}
      </button>
      {status ? <p className="pd-waitlist-ok">{status}</p> : null}
      {error ? <p className="pd-waitlist-err">{error}</p> : null}
      <p className="pd-waitlist-hint">
        또는{" "}
        <a href={personadiaryCopy.links.contact}>hello@personadiary.com</a>으로
        직접 문의할 수 있습니다.
      </p>
    </form>
  );
}

export function PersonadiaryWaitlist({ embedUrl }: { embedUrl?: string | null }) {
  const url = embedUrl?.trim();
  return (
    <section id="waitlist" aria-labelledby="pd-waitlist-title" className="pd-waitlist">
      <h2 id="pd-waitlist-title">사전 알림 · 관심 등록</h2>
      <p className="pd-waitlist-lead">
        프리뷰 단계입니다. 출시 알림은 이메일로만 받으며, 결제·일기 저장은 아직
        제공하지 않습니다.
      </p>
      {url ? (
        <div className="pd-waitlist-embed">
          <iframe
            src={url}
            title="personadiary waitlist"
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
        </div>
      ) : (
        <PersonadiaryWaitlistForm />
      )}
    </section>
  );
}
