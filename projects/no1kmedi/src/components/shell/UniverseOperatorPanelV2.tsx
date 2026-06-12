"use client";

import { useState } from "react";
import {
  OPERATOR_MOCK_SESSIONS,
  OPERATOR_PANEL_ENABLED,
  type OperatorMockSession,
} from "@/lib/universeHubOperatorMockV2";

function fsmLabel(state: OperatorMockSession["fsmState"]): string {
  const map = {
    normal: "NORMAL",
    elevated: "ELEVATED",
    cooldown: "COOLDOWN",
    human_handoff: "HUMAN",
  } as const;
  return map[state];
}

export function UniverseOperatorPanelV2() {
  const [selectedId, setSelectedId] = useState(OPERATOR_MOCK_SESSIONS[0]?.sessionId ?? "");

  if (!OPERATOR_PANEL_ENABLED) {
    return (
      <section className="universe-hub-operator-gate" aria-labelledby="operator-gate-title">
        <h1 id="operator-gate-title" className="universe-hub-plugin-title">
          운영자 패널 (internal)
        </h1>
        <p className="universe-hub-plugin-body">
          이 경로는 <code>NEXT_PUBLIC_UNIVERSE_HUB_OPERATOR_PANEL=1</code> 빌드에서만 활성화됩니다. 실고객
          데이터·SEND 게이트와 합선되지 않습니다.
        </p>
        <p className="universe-hub-disclaimer">SEND_GATE HOLD · customer_provided 업로드 UI 없음</p>
      </section>
    );
  }

  const selected = OPERATOR_MOCK_SESSIONS.find((s) => s.sessionId === selectedId) ?? OPERATOR_MOCK_SESSIONS[0];

  return (
    <article className="universe-hub-operator" aria-labelledby="operator-panel-title">
      <header>
        <p className="universe-hub-plugin-lane">operator_console_v1 · mock only</p>
        <h1 id="operator-panel-title" className="universe-hub-plugin-title">
          WTT 운영자 패널
        </h1>
        <p className="universe-hub-plugin-body">
          합성·마스킹 세션 큐 — FSM 상태·위험 점수 미리보기. 라이브 인입·실고객 코퍼스 연결 없음.
        </p>
      </header>

      <div className="universe-hub-operator-layout">
        <ul className="universe-hub-operator-queue" aria-label="세션 큐">
          {OPERATOR_MOCK_SESSIONS.map((row) => (
            <li key={row.sessionId}>
              <button
                type="button"
                className={
                  row.sessionId === selected?.sessionId
                    ? "universe-hub-operator-queue-btn is-active"
                    : "universe-hub-operator-queue-btn"
                }
                onClick={() => setSelectedId(row.sessionId)}
              >
                <span className="universe-hub-operator-queue-id">{row.sessionId}</span>
                <span className={`universe-hub-fsm universe-hub-fsm--${row.fsmState}`}>
                  {fsmLabel(row.fsmState)}
                </span>
              </button>
            </li>
          ))}
        </ul>

        {selected ? (
          <div className="universe-hub-operator-detail">
            <dl className="universe-hub-operator-meta">
              <div>
                <dt>Domain</dt>
                <dd>{selected.domainTag}</dd>
              </div>
              <div>
                <dt>Risk</dt>
                <dd>{selected.riskScore}</dd>
              </div>
              <div>
                <dt>FSM</dt>
                <dd>{fsmLabel(selected.fsmState)}</dd>
              </div>
            </dl>
            <p className="universe-hub-operator-preview">{selected.preview}</p>
            <ul className="universe-hub-operator-labels">
              {selected.labels.map((label) => (
                <li key={label}>
                  <span className="universe-hub-icp-pill">{label}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      <footer className="universe-hub-compliance-footer">
        <span className="universe-hub-compliance-tag universe-hub-compliance-tag--hold">SEND HOLD</span>
        <p>예시 SSOT: data/wtt/examples/wtt_operator_panel_sessions_v1.example.jsonl</p>
      </footer>
    </article>
  );
}
