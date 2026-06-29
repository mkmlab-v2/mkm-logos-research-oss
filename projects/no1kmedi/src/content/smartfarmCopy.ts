/**
 * B2B smart-farm landing copy (farm.jema-ai.com).
 * SSOT: docs/final/artifacts/smartfarm_public_copy_factlock_v1.md
 * Align: smartfarm_geumsan_6channel_valve_mapping_v1.json · smartfarm_qubics_contract_signed_v1.json
 */
export const smartfarmCopy = {
  seo: {
    title: "MKM 농업 IoT SI | 노지 관수·API 연동",
    description:
      "주식회사 목소리네트워크 — 하드웨어 제조가 아닌 관수 IoT 소프트웨어 SI. 6채널·토양센서 MQTT/API 연동, 안전 규칙·운영 로그. 파일럿: 충남 금산 노지(연동 dry-run 완료, 현장 Go-Live 전).",
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
    operator: "농장 운영",
    enterprise: "기업·기술 허브",
  },
  flow: {
    title: "노지 스마트관수 — 전체 데이터 흐름",
    lead:
      "밭 안은 무선(LoRa 등)으로 모으고, 게이트웨이 1대가 농장 라우터(Ethernet·LTE 등)를 통해 당사 서버에 올립니다. 수집·제어·안전 규칙은 MKM 소프트웨어가 담당합니다. (제조사·면적·프로토콜은 파트너 PDF·현장 스펙에 따름)",
    fieldLabel: "현장 (금산 파일럿 · 점적)",
    cloudLabel: "인터넷 · API / MQTT",
    serverLabel: "MKM 서버 · 농장주 앱",
    nodes: {
      tanks: "맹물 · 배양액 탱크",
      valves: "밸브 6채널 (맹물·양액·구역 4 — 맹물·양액 동시 OPEN 금지)",
      drip: "Y · 여과 · 펌프 → 점적 호스",
      sensors: "토양 센서 2~3",
      gateway: "LoRa → MQTT 게이트웨이 (G300) → 농장 라우터",
      server: "수집 · 이력 · 알람 · 제어 명령 (정책 게이트)",
      app: "모니터링 · 수동 개폐 · 안전 게이트 (운영 UI 단계적 오픈)",
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
        scope: "서버·운영 앱, 6채널 안전 규칙, MQTT/API 연동, 정책 기반 관수(현장 Go-Live·튜닝 후)",
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
      ["LTE/USIM", "게이트웨이 1대당 1장 · 당사 개통", "동일 원칙 · 대수만 증가 가능"],
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
      "우리는 펌프·탱크·점적 설비를 직접 시공하지 않습니다. 파트너 IoT(6채널·토양센서·MQTT)와 연결하고, 토양 수분·안전 규칙·운영 로그를 당사 서버에서 제공합니다.",
    cta_primary: "하드웨어 파트너 제안",
    cta_secondary: "아키텍처 보기",
  },
  architecture: {
    title: "2탱크 · 6채널 · 1게이트웨이",
    lead: "맹물·배양액 분리, 동시 혼합 없이 순차 제어. 구역 밸브 4채널. 연동: telemetry / MQTT control (dry-run 검증 완료).",
    steps: [
      { label: "맹물 탱크", detail: "토양 수분·정책 기반 관수 (ch1)" },
      { label: "배양액 탱크", detail: "등록 배치·게이트 통과 후 (ch2, 저빈도)" },
      { label: "Y 합류 · 여과 · 펌프", detail: "농장 설비 — IoT 범위 외" },
      { label: "점적 · 노지 4구역", detail: "본선 ch3·ch5 / 데모 ch4(커피 50주·~20평)·ch6" },
    ],
    specs: [
      { k: "게이트웨이", v: "Ethernet → 농장 라우터 · 릴레이 6채널 (D202)" },
      { k: "토양 센서", v: "무선 2대 출고 (D301/D302) · 구역 확대 시 증설" },
      { k: "밸브", v: "솔레노이드 6 (맹물·양액·구역 4)" },
      { k: "통신", v: "농장 인터넷(LTE 등) · qbsv4 MQTT" },
    ],
  },
  comms: {
    title: "통신: LoRa(밭) + Ethernet(게이트웨이)",
    lead: "센서마다 USIM이 필요하지 않습니다. 게이트웨이는 농장 라우터에 유선 연결하고, 상행 인터넷은 농장 LTE·광랜 등 현장 조건을 따릅니다.",
    layers: [
      {
        label: "현장 무선",
        detail: "토양 센서 → 게이트웨이 G300 (LoRa·CoCoNET, 벤더 스펙)",
        tag: "센서 USIM 없음",
      },
      {
        label: "상행 링크",
        detail: "게이트웨이 Ethernet → 농장 라우터 → MKM 서버 (MQTT qbsv4)",
        tag: "농장 인터넷",
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
      ["하드웨어 파트너", "게이트웨이·6채널 제어기·토양 센서·솔레노이드 6, 결선·자가설치·1년 A/S"],
      ["MKM (소프트웨어)", "정책 기반 관수·6채널 안전·알람·이력·MQTT/API 연동 (현장 Go-Live 전 dry-run 완료)"],
      ["견적 제외", "USIM·월 데이터 요금, VAT, 농장 설비·배관 공사"],
    ],
  },
  partnership: {
    title: "하드웨어 파트너 요건",
    lead: "반쪽 턴키(센서·게이트웨이·밸브·결선·시운전) 견적·기술 회신용 조건입니다.",
    items: [
      {
        title: "API / MQTT / Modbus",
        body: "REST, MQTT, Modbus 중 1종 이상 PDF. 당사 서버에서 센서 수집·릴레이 채널별 제어 가능해야 합니다.",
      },
      {
        title: "반쪽 턴키",
        body: "탱크·펌프·점적 배관은 농장·설비업 완료 후. 귀사는 센서·게이트웨이·밸브·자가설치·1년 A/S.",
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
    status: "큐빅스 6채널 장비 계약·MQTT 연동 dry-run 완료 — 현장 cid·ACK·72h 안정성 확인 후 Go-Live",
    note: "운영 앱·자동 모드는 Go-Live KPI 통과 후 단계 오픈. 1,000평 확장은 「확장 설계」 참고.",
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
      "「AI·LLM 자동관수」가 아닌 정책·센서 기반 관수입니다. 성능 수치는 Go-Live KPI 아티팩트 없이 단정하지 않습니다.",
    ],
  },
  footer: {
    hub: "https://app.jema-ai.com/enterprise",
    home: "https://jema-ai.com",
  },
} as const;
