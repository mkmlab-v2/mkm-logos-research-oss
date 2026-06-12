"use client";

import { useId, useState } from "react";

type Props = {
  defaultOpen?: boolean;
};

export function UniverseHubDisclaimerCollapsible({ defaultOpen = true }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <div className="universe-hub-disclaimer-block">
      <button
        type="button"
        className="universe-hub-disclaimer-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        면책·격벽 고지 {open ? "접기" : "펼치기"}
      </button>
      {open ? (
        <div id={panelId} className="universe-hub-disclaimer-panel">
          <p>
            B2B·페르소나 가드·EPB 맞춤은{" "}
            <a href="/hub/customize" className="universe-hub-inline-link">
              AI 맞춤·가드 (기업)
            </a>
            로 분리됩니다. 소비자 원퀘스천과 엔진·데이터를 합치지 않습니다.
          </p>
          <p>
            [NON-MEDICAL] [NON-DETERMINISTIC] [FINANCIAL-RISK] 관측·참고용이며 투자·의료·실매매 지시가
            아닙니다.
          </p>
          <p>[DRAFT] research_only · SEND_GATE HOLD · Track A·live 자동 합선 없음</p>
        </div>
      ) : null}
    </div>
  );
}
