/**
 * B2B smart-farm landing copy (farm.jema-ai.com).
 * Align with docs/final/artifacts/smartfarm_geumsan_vendor_rfq_v2_2026-05-18.md
 * Public-facing guardrails: docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md
 */
export const smartfarmCopy = {
  seo: {
    title: "MKM 농업 IoT SI | 노지 관수·API 연동",
    description:
      "주식회사 목소리네트워크 — 하드웨어 제조가 아닌 스마트관수 SI. LTE 게이트웨이·2밸브·토양센서 API 연동, 운영 앱·안전 규칙. 파일럿: 충남 금산 노지 커피.",
  },
  brand: {
    legal: "주식회사 목소리네트워크",
    product: "MKM Agriculture IoT",
    productShort: "MKM",
    productLine: "Agriculture IoT",
    tagline: "노지·시설 데이터 제어 — 하드웨어는 파트너, 운영은 소프트웨어",
  },
  publicUrl: "https://farm.jema-ai.com",
  a11y: {
    skip_to_main: "본문으로 건너뛰기",
    nav_aria_label: "농업 IoT",
    mail_subject: "[농업 IoT 파트너] 하드웨어·API 연동 제안",
  },
  nav: {
    flow: "시스템 흐름",
    architecture: "아키텍처",
    comms: "통신",
    roles: "역할 분담",
    scope: "납품 범위",
    scale: "확장 설계",
    partnership: "파트너십",
    pilot: "파일럿",
    contact: "문의",
    enterprise: "기업·기술 허브",
  },
  flow: {
    title: "노지 스마트관수 — 전체 데이터 흐름",
    lead:
      "밭 안은 무선(LoRa 등)으로 모으고, 게이트웨이 1대가 LTE·USIM으로 당사 서버에 올립니다. 수집·제어·안전 규칙은 MKM 소프트웨어가 담당합니다. (제조사·면적·프로토콜은 파트너 PDF·현장 스펙에 따름)",
    fieldLabel: "현장 (금산 파일럿 · 점적)",
    cloudLabel: "인터넷 · API / MQTT",
    serverLabel: "MKM 서버 · 농장주 앱",
    nodes: {
      tanks: "맹물 · 배양액 탱크",
      valves: "밸브 A · B (동시 OPEN 금지)",
      drip: "Y · 여과 · 펌프 → 점적 호스",
      sensors: "토양 센서 2~3",
      gateway: "LoRa → MQTT 게이트웨이 + USIM 1",
      server: "수집 · 이력 · 알람 · 제어 명령",
      app: "그래프 · 수동 개폐 · 안전 게이트",
    },
    protocolNote:
      "연동: REST / MQTT / Modbus 중 1종 이상(PDF). Phase 0(약 2주) 벤더 앱 병행 가능 → Phase 1부터 당사 서버·앱.",
    caption:
      "도면은 300평·1구역·점적 파일럿 기준 예시입니다. 스프링클러·온실 센서 구성과 다를 수 있습니다.",
  },
  roles: {
    title: "시공·소프트웨어 역할 분담",
    lead: "배관 공사와 IoT 장비, 데이터 운영을 분리해 견적·책임 범위를 명확히 합니다.",
    items: [
      {
        who: "농장주 · 설비",
        scope: "맹물·배양액 탱크, Y합류, 여과, 펌프, 점적 본관, 220V 인입",
        tag: "IoT 범위 외",
      },
      {
        who: "하드웨어 파트너",
        scope: "토양 센서, LTE 게이트웨이·제어기(릴레이≥2), 솔레노이드 2, 결선·현장 1일·1년 A/S",
        tag: "반쪽 턴키",
      },
      {
        who: "MKM (당사)",
        scope: "USIM 자체 개통 안내, 서버·앱, 2밸브 안전, API 연동, 자동관수(승인·튜닝 후)",
        tag: "소프트웨어 SI",
      },
    ],
  },
  scale: {
    title: "면적 확장 (300평 → 1,000평 참고)",
    lead:
      "USIM·게이트웨이만 늘린다고 면적이 커지지 않습니다. 센서·구역·펌프·밸브·무선 거리를 함께 설계합니다.",
    columns: ["구분", "300평 (본 건)", "~1,000평 (참고)"],
    rows: [
      ["구역", "1구역 쇼룸", "1~2구역 (현장·무선 실측)"],
      ["게이트웨이", "1식", "1~2식 (벤더 권장안)"],
      ["USIM", "게이트웨이 1대당 1장 · 당사 개통", "동일 원칙 · 대수만 증가 가능"],
      ["토양 센서", "2~3", "4~6 (배치 간격은 PDF·실측)"],
      ["LoRa 커버", "벤더 스펙·1구역 면적", "게이트웨이당 권장 거리·평 재확인"],
      ["견적", "IoT 300~500만 원 상한(USIM·월요금 제외)", "별도 증설 견적"],
    ],
    note: "2,000평 이상은 다구역·릴레이·설비 증설을 별도 RFQ로 검토합니다.",
  },
  hero: {
    eyebrow: "B2B · Smart Irrigation SI",
    title: "검증된 장비를 API로 연결하는\n노지 관수 통합 파트너",
    lead:
      "우리는 펌프·탱크·점적 설비를 직접 시공하지 않습니다. 국내 제조사 LTE/무선 센서·솔레노이드와 API로 연결하고, 토양 수분·2밸브 안전·운영 로그를 당사 서버·앱에서 제공합니다.",
    cta_primary: "하드웨어 파트너 제안",
    cta_secondary: "아키텍처 보기",
  },
  architecture: {
    title: "2탱크 · 2밸브 · 1게이트웨이",
    lead: "맹물·배양액(발효액) 분리, 동시 혼합 없이 순차 제어. Phase 1 연동: telemetry / control API v1.",
    steps: [
      { label: "맹물 탱크", detail: "토양 수분 기반 자동 관수 (채널 A)" },
      { label: "배양액 탱크", detail: "등록 배치·시간 상한 (채널 B, 저빈도)" },
      { label: "Y 합류 · 여과 · 펌프", detail: "농장 설비 — IoT 범위 외" },
      { label: "점적 · 노지", detail: "대표 파일럿 ~300평(1구역)" },
    ],
    specs: [
      { k: "게이트웨이", v: "LTE · 릴레이 ≥2채널 (A/B 독립)" },
      { k: "토양 센서", v: "무선 복합 2~3 (수분·지온·EC)" },
      { k: "밸브", v: "솔레노이드 2 (맹물 / 배양액)" },
      { k: "통신", v: "USIM 당사 자체 개통 · Wi-Fi 불필요" },
    ],
  },
  comms: {
    title: "통신: LoRa(밭) + LTE/USIM(서버)",
    lead: "센서마다 USIM이 필요한 구조가 아닙니다. 게이트웨이 1대당 USIM 1장은 인터넷 상행용이며, 평수 상한을 뜻하지 않습니다.",
    layers: [
      {
        label: "현장 무선",
        detail: "토양 센서 2~3 → 게이트웨이 (LoRa·Sub-GHz 등, 벤더 스펙)",
        tag: "USIM 없음",
      },
      {
        label: "상행 링크",
        detail: "게이트웨이 1 + USIM 1 → MKM 서버·운영 앱 (Wi-Fi 없는 노지)",
        tag: "당사 개통",
      },
    ],
    note: "300평 1구역 파일럿 기준. 1,000~2,000평 확장은 센서·구역·게이트웨이 증설을 별도 설계합니다.",
  },
  scope: {
    title: "역할·납품 범위 (반쪽 턴키)",
    lead: "농장 설비(탱크·펌프·점적 배관)와 IoT 반쪽 턴키를 분리합니다. 견적·회신 시 배관·펌프 공사비는 제외해 주십시오.",
    columns: ["구분", "범위"],
    rows: [
      ["농장·설비 (IoT 외)", "맹물·배양액 탱크, Y합류, 여과, 펌프, 점적 본관, 220V 인입"],
      ["하드웨어 파트너", "LTE 게이트웨이·제어기 1, 토양 센서 2~3, 솔레노이드 2, 결선·현장 1일·1년 A/S"],
      ["MKM (소프트웨어)", "관수 자동화·2밸브 안전·알람·이력·API 연동 v1 (REST/MQTT/Modbus PDF)"],
      ["견적 제외", "USIM·월 데이터 요금, VAT, 농장 설비·배관 공사"],
    ],
  },
  partnership: {
    title: "하드웨어 파트너 요건",
    lead: "반쪽 턴키(센서·게이트웨이·밸브·결선·시운전) 견적·기술 회신용 조건입니다.",
    items: [
      {
        title: "API / MQTT / Modbus",
        body: "REST, MQTT, Modbus 중 1종 이상 PDF. 당사 서버에서 센서 수집·릴레이 A/B 개별 제어 가능해야 합니다.",
      },
      {
        title: "반쪽 턴키",
        body: "탱크·펌프·점적 배관은 농장·설비업 완료 후. 귀사는 센서·LTE·밸브 2·현장 1일·1년 A/S.",
      },
      {
        title: "안전·디커플링",
        body: "v1: A+B 동시 OPEN 자동 혼합 제외. 배양액 pH·EC는 농장 자체 측정·앱 등록 후 투입.",
      },
    ],
  },
  pilot: {
    title: "진행 파일럿",
    site: "충남 금산군 · 노지 점적 커피 약 300평",
    status: "하드웨어 파트너 견적·API 회신 진행 중",
    note: "USIM·운영 앱은 당사(MKM). 1,000평 이상 확장은 아래 「확장 설계」 표 참고.",
  },
  contact: {
    title: "B2B 사업 제휴",
    email: "support@mkmlife.com",
    hint: "제목에 [농업 IoT 파트너]를 넣어 주시면 담당 배정이 빠릅니다.",
    biz_reg: "사업자등록번호 628-86-01742",
  },
  disclaimer: {
    title: "고지",
    items: [
      "본 페이지는 B2B·기술·파트너십 소개용입니다. 수확량·투자 수익·의료·임상 효과를 보장하지 않습니다.",
      "자동 관수·알람은 파일럿 조건·현장 튜닝·통신 상태에 따르며, 최종 농작업 판단은 농장주·전문가 책임입니다.",
      "성능·적중률 등 수치는 검증 아티팩트 없이 단정하지 않습니다. 상세 RFQ는 메일 요청 시 제공합니다.",
    ],
  },
  footer: {
    hub: "https://app.jema-ai.com/enterprise",
    home: "https://jema-ai.com",
  },
} as const;
