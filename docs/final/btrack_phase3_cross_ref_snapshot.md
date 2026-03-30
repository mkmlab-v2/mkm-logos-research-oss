# B-Track Phase3 — CROSS_REF_DSS_TO_STATES_DRAFT 송환 스냅샷

**용도**: NotebookLM Phase3 대조 노트 전용. 정본 SSOT는 `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json`(v2). 아래는 동 파일의 `generated_at_utc` 및 엔트리 요약과 **기계적으로 동기화**(평문 ENTRY / 축약 JSON).

**SSOT 시각**: `generated_at_utc`는 JSON 상단 값을 따른다(커밋 시각과 별개일 수 있음).

```json
{
  "schema": "cross_ref_dss_to_states_draft_v2",
  "disclaimer": "B-Track parallel-corpus draft only; not A-Track SSOT; trading engine must not load this path by default.",
  "generated_at_utc": "2026-03-30T22:00:00+00:00",
  "entries": [
    {
      "source_id": "1QM 1:1-7 (War Scroll, Col.1)",
      "link_type": "thematic",
      "state_candidate_id": 1,
      "rationale": "B-Track DSS: 빛의 아들들 vs 벨리알·키팀·언약 위반자의 개전 서사. A-Track 비유 후보(가설): 극단적 방향성·돌파 국면 — dual_regime·리스크 캡과 무관."
    },
    {
      "source_id": "1Enoch 10:4-6 (Charles / Wikisource ch.10)",
      "link_type": "thematic",
      "state_candidate_id": 15,
      "rationale": "B-Track Apocrypha: 아자젤 결박·어둠·대심판의 불. A-Track 비유 후보(가설): 청산·극단 공포(Capitulation) — State 16 후보와 인접 축으로 별도 행 구분 가능."
    },
    {
      "source_id": "1Enoch 10:7 (Charles / Wikisource ch.10)",
      "link_type": "thematic",
      "state_candidate_id": 2,
      "rationale": "B-Track Apocrypha: 타락한 땅의 치유 선포·멸망 방지. A-Track 비유 후보(가설): 심판 국면 이후 질서·반등 서사(V·전환) — 확정 신호 아님."
    },
    {
      "source_id": "Jubilees 6:29-38 + 364-day notes (btrack_apocrypha_jubilees_ch6_excerpt_charles.md; btrack_apocrypha_jubilees_calendar_364.md)",
      "link_type": "temporal",
      "state_candidate_id": 8,
      "rationale": "B-Track Apocrypha: 364일·분기·음력과의 긴장, 정해진 절기 질서. A-Track 비유 후보(가설): 하드코딩된 반감기·주기 신뢰·저변동 인내 — 횡보·매집 담론과 병치 가능."
    },
    {
      "source_id": "1QS IX 10-11 (Community Rule; Eng. citation in btrack_dss_1QS_sectarian_context.md)",
      "link_type": "thematic",
      "state_candidate_id": 3,
      "rationale": "B-Track DSS: 예언자와 아론·이스라엘의 기름부음 받은 자에 대한 기대. A-Track 비유 후보(가설): 규율·언약 공동체·장기 신념 — HODL 담론은 비유일 뿐 자동 트리거 금지."
    },
    {
      "source_id": "1QpHab col.VII (Pesher Habakkuk; crisis interpretation layer — scholarly citation TBD)",
      "link_type": "thematic",
      "state_candidate_id": 4,
      "rationale": "B-Track DSS: 하바국 해석(페셔)의 ‘위기를 성경으로 재독’ 레이어. A-Track 비유 후보(가설): 규범·도덕 프레임(칠선 언약 맥락)과 시장 서사 병치 — geometry/trigger 아님; Fact-Lock 벤치만."
    },
    {
      "source_id": "11QT XLVI-XLVII (Temple Scroll; festival/calendar layer — academic edition TBD)",
      "link_type": "temporal",
      "state_candidate_id": 5,
      "rationale": "B-Track DSS: 성전·절기 일정 규범 텍스트. A-Track 대비: Ezra 명단 행은 ‘복귀 코호트’ 스냅샷 — 달력 DSS와 주제만 병치(벤치); 인과·트리거 금지."
    },
    {
      "source_id": "4Q319 (Otot / priestly cycle signal text — edition siglum TBD)",
      "link_type": "temporal",
      "state_candidate_id": 6,
      "rationale": "B-Track DSS: 제사장 주기·신호 표류. A-Track 대비: Nehemiah 복귀자 명단 행 — 인구/재건 흐름과 ‘주기 신호’ 담론만 병치(벤치)."
    },
    {
      "source_id": "4Q169 frags 3-4 ii (Nahum Pesher; ‘planner of evil’ discourse — transcription TBD)",
      "link_type": "thematic",
      "state_candidate_id": 7,
      "rationale": "B-Track DSS: 나훔 페셔의 악행 귀속·심판 화법. A-Track 대비: 시36 ‘악인의 죄’ 서사와 주제 병치 — 수치/심리 트리거 아님."
    },
    {
      "source_id": "CD-A I-II (Damascus Document; ‘land’ / exile–return framing — bench citation TBD)",
      "link_type": "thematic",
      "state_candidate_id": 9,
      "rationale": "B-Track DSS: 공동체의 언약·지경 담론. A-Track 대비: 여호수아 지파 경계 점과 ‘땅·경계’ 메타만 병치 — 지리≠가격."
    }
  ]
}
```

**축 구분**: ENTRY_01·05·06·09·10은 DSS 규범·페셔·담론(대부분 `thematic`). ENTRY_02–03은 외경(1에녹, `thematic`). ENTRY_04는 희년서 달력(`temporal`). ENTRY_07–08은 성전 스크롤·오톳 등 **시간·주기 레이어**(`temporal`). 비트코인·실매매 트리거와 무관.

## 평문 엔트리 (NotebookLM 인덱싱용 — 코드펜스 밖)

ENTRY_01 | link_type=thematic | source_id=1QM 1:1-7 (War Scroll, Col.1) | state_candidate_id=1 | corpus=dss | theme=개전·이원론 돌파 가설 | rationale=B-Track DSS: 빛의 아들들 vs 벨리알·키팀·언약 위반자의 개전 서사. A-Track 비유 후보(가설): 극단적 방향성·돌파 국면 — dual_regime·리스크 캡과 무관.

ENTRY_02 | link_type=thematic | source_id=1Enoch 10:4-6 (Charles / Wikisource ch.10) | state_candidate_id=15 | corpus=apocrypha | theme=아자젤·극단 심판 가설 | rationale=B-Track Apocrypha: 아자젤 결박·어둠·대심판의 불. A-Track 비유 후보(가설): 청산·극단 공포(Capitulation) — State 16 후보와 인접 축으로 별도 행 구분 가능.

ENTRY_03 | link_type=thematic | source_id=1Enoch 10:7 (Charles / Wikisource ch.10) | state_candidate_id=2 | corpus=apocrypha | theme=치유·전환 가설 | rationale=B-Track Apocrypha: 타락한 땅의 치유 선포·멸망 방지. A-Track 비유 후보(가설): 심판 국면 이후 질서·반등 서사(V·전환) — 확정 신호 아님.

ENTRY_04 | link_type=temporal | source_id=Jubilees 6:29-38 + 364-day notes (btrack_apocrypha_jubilees_ch6_excerpt_charles.md; btrack_apocrypha_jubilees_calendar_364.md) | state_candidate_id=8 | corpus=pseudepigrapha | theme=364일·주기 질서 가설 | rationale=B-Track Apocrypha: 364일·분기·음력과의 긴장, 정해진 절기 질서. A-Track 비유 후보(가설): 하드코딩된 반감기·주기 신뢰·저변동 인내 — 횡보·매집 담론과 병치 가능.

ENTRY_05 | link_type=thematic | source_id=1QS IX 10-11 (Community Rule; Eng. citation in btrack_dss_1QS_sectarian_context.md) | state_candidate_id=3 | corpus=dss | theme=복수 메시아·규율 공동체 가설 | rationale=B-Track DSS: 예언자와 아론·이스라엘의 기름부음 받은 자에 대한 기대. A-Track 비유 후보(가설): 규율·언약 공동체·장기 신념 — HODL 담론은 비유일 뿐 자동 트리거 금지.

ENTRY_06 | link_type=thematic | source_id=1QpHab col.VII (Pesher Habakkuk; crisis interpretation layer — scholarly citation TBD) | state_candidate_id=4 | corpus=dss | theme=페셔·위기 재독 | rationale=B-Track DSS: 하바국 해석(페셔)의 ‘위기를 성경으로 재독’ 레이어. A-Track 비유 후보(가설): 규범·도덕 프레임(칠선 언약 맥락)과 시장 서사 병치 — geometry/trigger 아님; Fact-Lock 벤치만.

ENTRY_07 | link_type=temporal | source_id=11QT XLVI-XLVII (Temple Scroll; festival/calendar layer — academic edition TBD) | state_candidate_id=5 | corpus=dss | theme=성전·절기 규범 | rationale=B-Track DSS: 성전·절기 일정 규범 텍스트. A-Track 대비: Ezra 명단 행은 ‘복귀 코호트’ 스냅샷 — 달력 DSS와 주제만 병치(벤치); 인과·트리거 금지.

ENTRY_08 | link_type=temporal | source_id=4Q319 (Otot / priestly cycle signal text — edition siglum TBD) | state_candidate_id=6 | corpus=dss | theme=제사장 주기·신호 | rationale=B-Track DSS: 제사장 주기·신호 표류. A-Track 대비: Nehemiah 복귀자 명단 행 — 인구/재건 흐름과 ‘주기 신호’ 담론만 병치(벤치).

ENTRY_09 | link_type=thematic | source_id=4Q169 frags 3-4 ii (Nahum Pesher; ‘planner of evil’ discourse — transcription TBD) | state_candidate_id=7 | corpus=dss | theme=나훔 페셔·악행 귀속 | rationale=B-Track DSS: 나훔 페셔의 악행 귀속·심판 화법. A-Track 대비: 시36 ‘악인의 죄’ 서사와 주제 병치 — 수치/심리 트리거 아님.

ENTRY_10 | link_type=thematic | source_id=CD-A I-II (Damascus Document; ‘land’ / exile–return framing — bench citation TBD) | state_candidate_id=9 | corpus=dss | theme=언약·지경·유배 | rationale=B-Track DSS: 공동체의 언약·지경 담론. A-Track 대비: 여호수아 지파 경계 점과 ‘땅·경계’ 메타만 병치 — 지리≠가격.

공통 경고: disclaimer 필드 — A-Track SSOT 아님; 엔진이 기본 로드 금지; 후보(candidate)만 기록.
