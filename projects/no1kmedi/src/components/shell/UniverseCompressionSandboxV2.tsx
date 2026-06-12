"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

/** Client-only PoC ratio — not Track A SLA; ~24% proxy band for demo UX. */
function demoCompressionRatio(input: string): number {
  const trimmed = input.trim();
  if (!trimmed) return 0;
  const tokens = trimmed.split(/\s+/).length;
  const unique = new Set(trimmed.toLowerCase().split(/\s+/)).size;
  const repeatFactor = tokens > 0 ? unique / tokens : 1;
  const raw = 0.18 + repeatFactor * 0.12;
  return Math.min(0.28, Math.max(0.12, raw));
}

export function UniverseCompressionSandboxV2() {
  const [text, setText] = useState("");
  const [ran, setRan] = useState(false);

  const ratio = useMemo(() => demoCompressionRatio(text), [text]);
  const savingPct = Math.round(ratio * 1000) / 10;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setRan(true);
  }

  return (
    <div className="universe-hub-compression-sandbox">
      <p className="universe-hub-compression-badge">[DRAFT] · contributor PoC proxy · 비-SLA</p>
      <p className="universe-hub-compression-lead">
        로컬 데모 시뮬레이터입니다. 실험실 고정 스코어나 Track A 헤드라인과 동일시하지 마세요. 공개 참고치는
        per-SKU·오픈벤치 재현 체인 기준입니다.
      </p>

      <form className="universe-hub-compression-form" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="compression-demo-input">
          압축 데모 입력
        </label>
        <textarea
          id="compression-demo-input"
          className="universe-hub-compression-textarea"
          rows={6}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setRan(false);
          }}
          placeholder="B2B PoC용 샘플 텍스트를 붙여넣으세요 (API 미연결 · 오프라인 데모)"
          maxLength={8000}
        />
        <button type="submit" className="universe-hub-compression-submit">
          데모 압축 시뮬 실행
        </button>
      </form>

      {ran && text.trim() ? (
        <div className="universe-hub-compression-result" role="status">
          <p className="universe-hub-compression-result-head">
            proxy 절감률 <strong>~{savingPct}%</strong> <span className="universe-hub-compression-muted">[DRAFT]</span>
          </p>
          <p className="universe-hub-compression-result-note">
            오프라인 휴리스틱 데모 — 네트워크·실 API·frozen Track A 벤치 아님.
          </p>
        </div>
      ) : null}

      <p className="universe-hub-disclaimer universe-hub-disclaimer--compact">
        SEND_GATE: HOLD · B→A 자동 합선 없음 · 실고객 SLA 단정 금지
      </p>

      <div className="universe-hub-compression-ctas">
        <Link className="universe-hub-cta" href="/enterprise/apply">
          B2B 상담·사전 감사 신청
        </Link>
        <Link className="universe-hub-cta universe-hub-cta--ghost" href="/hub/developer">
          개발자 샌드박스 ↗
        </Link>
      </div>
    </div>
  );
}
