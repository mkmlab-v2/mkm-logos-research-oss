/**
 * Operator PWA copy — Fact-Lock aligned.
 * SSOT: docs/final/artifacts/smartfarm_public_copy_factlock_v1.md
 */
export const smartfarmOperatorCopy = {
  seo: {
    title: "금산 농장 운영 | MKM Agriculture IoT",
    description:
      "토양 센서·6채널 밸브 모니터링·수동 제어·비상정지. 정책 기반 관수 — LLM 자동 완성 아님.",
  },
  brand: {
    title: "농장 운영",
    subtitle: "금산 파일럿 · 6채널",
    back: "B2B 소개",
  },
  status: {
    connected: "서버 연결됨",
    disconnected: "서버 연결 안 됨",
    stale: "센서 데이터 지연",
    comm_down: "통신 끊김",
  },
  sections: {
    sensors: "토양 센서",
    valves: "밸브 (6채널)",
    safety: "안전",
    events: "최근 이벤트",
    auto: "자동 평가",
  },
  sensor: {
    moisture: "수분",
    temp: "지온",
    ec: "EC",
    no_data: "데이터 없음",
    unit_moisture: "%",
    unit_temp: "°C",
    unit_ec: "µS/cm",
  },
  valve: {
    open: "열기",
    close: "닫기",
    open_blocked: "맹물·양액 동시 개방 불가",
    pulse_note: "순차 펄스만 · 동시 다채널 금지",
  },
  safety: {
    emergency: "비상 정지",
    emergency_hint: "모든 채널 닫기 명령 전송",
    auto_mode: "자동 평가 보기",
    auto_on: "켜짐 (제안만 표시)",
    auto_off: "꺼짐",
    manual_only: "현장 Go-Live 전: 수동·로그 중심",
  },
  auto: {
    decision_execute: "관수 제안 있음",
    decision_skip: "관수 보류",
    no_suggestion: "제안 없음",
    evaluate: "지금 평가",
  },
  events: {
    empty: "이벤트 없음",
  },
  disclaimer: {
    title: "운영 안내",
    items: [
      "본 화면은 정책·센서 기반 운영 도구입니다. LLM이 밸브를 직접 제어하지 않습니다.",
      "최종 농작업·이상 시 밸브·펌프를 수동으로 차단하세요.",
      "자동 모드는 Go-Live KPI 통과 후 단계적으로 오픈됩니다.",
    ],
  },
  errors: {
    control_failed: "명령 전송 실패",
    interlock: "맹물(ch1)과 배양액(ch2)은 동시에 열 수 없습니다.",
  },
} as const;
