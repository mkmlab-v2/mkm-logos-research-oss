/**
 * Operator panel mock rows — mirrors data/wtt/examples/wtt_operator_panel_sessions_v1.example.jsonl (subset).
 * customer_provided: false · SEND HOLD · not live intake.
 */

export type OperatorMockFsmState = "normal" | "elevated" | "cooldown" | "human_handoff";

export type OperatorMockSession = {
  sessionId: string;
  domainTag: string;
  fsmState: OperatorMockFsmState;
  riskScore: number;
  preview: string;
  labels: string[];
};

export const OPERATOR_MOCK_SESSIONS: OperatorMockSession[] = [
  {
    sessionId: "op-panel-cs-001",
    domainTag: "customer-support-chat",
    fsmState: "elevated",
    riskScore: 62,
    preview: "주문번호 환불 요청 · 마스킹된 연락처 콜백",
    labels: ["masked", "research_only", "operator_panel"],
  },
  {
    sessionId: "op-panel-cs-003",
    domainTag: "customer-support-chat",
    fsmState: "human_handoff",
    riskScore: 88,
    preview: "VIP 대기 · 복붙 답변 거부 · 매니저 연결 요구",
    labels: ["masked", "internal_dogfood"],
  },
  {
    sessionId: "op-panel-cs-012",
    domainTag: "customer-support-chat",
    fsmState: "cooldown",
    riskScore: 71,
    preview: "약관 불일치 주장 · 챗봇 응답 이탈 위험",
    labels: ["masked", "not_customer_data"],
  },
];

export const OPERATOR_PANEL_ENABLED =
  process.env.NEXT_PUBLIC_UNIVERSE_HUB_OPERATOR_PANEL === "1";
