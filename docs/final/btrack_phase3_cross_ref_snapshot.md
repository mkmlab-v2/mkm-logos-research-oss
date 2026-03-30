# B-Track Phase3 — CROSS_REF_DSS_TO_STATES_DRAFT 송환 스냅샷

**용도**: NotebookLM Phase3 대조 노트 전용. 정본 SSOT는 `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json`(v2). 아래는 동 파일의 `generated_at_utc` 및 엔트리 요약과 **기계적으로 동기화**(평문 ENTRY / 축약 JSON).

**SSOT 시각**: `generated_at_utc`는 JSON 상단 값을 따른다(커밋 시각과 별개일 수 있음).

**행 수**: **16행** (ENTRY_01–16) — `LOGOS_STATE_MAPPING_V1`의 `state_id` 1–16 각각 1행; 전문 필드는 항상 SSOT JSON을 따른다.

```json
{
  "schema": "cross_ref_dss_to_states_draft_v2",
  "disclaimer": "B-Track parallel-corpus draft only; not A-Track SSOT; trading engine must not load this path by default. Source standard (proxies, not autographs): bulk apocrypha in-repo uses Sefaria-tagged JSONL (`data/logos/manuscripts/apocrypha_std.jsonl`, per-row `source`). Excerpt MDs may cite R.H. Charles, Charlesworth, Wikisource, or similar. DSS `satellite_ref` lines are thematic alignment notes and do not assert Oxford/DJD diplomatic text unless that edition is explicitly named there. Acquisition of closed-licence critical editions (e.g. DJD) is out of scope for this draft.",
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
      "source_id": "1QpHab (1Q15) col.VII — Pesher Habakkuk; plates: The Dead Sea Scrolls of St. Mark's Monastery I (New Haven: ASOR, 1950); trans./lineation: e.g. García Martínez & Tigchelaar, The Dead Sea Scrolls Study Edition (Brill) — verify col/line against chosen edition",
      "link_type": "thematic",
      "state_candidate_id": 4,
      "rationale": "B-Track DSS: 하바국 해석(페셔)의 ‘위기를 성경으로 재독’ 레이어. A-Track 비유 후보(가설): 규범·도덕 프레임(칠선 언약 맥락)과 시장 서사 병치 — geometry/trigger 아님; Fact-Lock 벤치만."
    },
    {
      "source_id": "11QT (11Q19) cols.XLVI–XLVII — Temple Scroll; Yadin, The Temple Scroll (Jerusalem: Israel Exploration Society, 1977); cf. DJD XXIII (11Q19); festival/calendar layer — verify col range to edition",
      "link_type": "temporal",
      "state_candidate_id": 5,
      "rationale": "B-Track DSS: 성전·절기 일정 규범 텍스트. A-Track 대비: Ezra 명단 행은 ‘복귀 코호트’ 스냅샷 — 달력 DSS와 주제만 병치(벤치); 인과·트리거 금지."
    },
    {
      "source_id": "4Q319 (4QOtot) — priestly cycle / Otot; DJD XXI: S. Talmon et al., Calendrical Texts (Oxford: Clarendon, 2001); verify fragment sigla to plate",
      "link_type": "temporal",
      "state_candidate_id": 6,
      "rationale": "B-Track DSS: 제사장 주기·신호 표류. A-Track 대비: Nehemiah 복귀자 명단 행 — 인구/재건 흐름과 ‘주기 신호’ 담론만 병치(벤치)."
    },
    {
      "source_id": "4Q169 (4QpNah) frags 3–4 col.ii — Pesher Nahum; editio princeps DJD V (J.M. Allegro, Oxford: Clarendon, 1968); modern trans. e.g. DSS Study Edition (Brill) — verify frag/col to edition; ‘planner of evil’ discourse (bench label)",
      "link_type": "thematic",
      "state_candidate_id": 7,
      "rationale": "B-Track DSS: 나훔 페셔의 악행 귀속·심판 화법. A-Track 대비: 시36 ‘악인의 죄’ 서사와 주제 병치 — 수치/심리 트리거 아님."
    },
    {
      "source_id": "CD-A I–II (Damascus Document, Cairo Geniza ms A); J.H. Charlesworth, The Damascus Document (Tübingen: Mohr, PTSDSSP 1995); Qumran parallels 4Q266–273 — DJD XVIII (Baumgarten, 1996) — bench: land/exile–return framing",
      "link_type": "thematic",
      "state_candidate_id": 9,
      "rationale": "B-Track DSS: 공동체의 언약·지경 담론. A-Track 대비: 여호수아 지파 경계 점과 ‘땅·경계’ 메타만 병치 — 지리≠가격."
    },
    {
      "source_id": "1QM.1.1",
      "link_type": "analogy_bench",
      "state_candidate_id": 13,
      "canonical_ref": "1Chr.14.6",
      "rationale": "[HYPO] 금화교역 상전이 벤치 — 1QM·에스겔 해석 레이어; 전문은 SSOT JSON.",
      "note": "NL v2.1 관측: 맥락 오염·False equivalence 리스크; [HYPO] 승격 보류. 전문 note는 `CROSS_REF_DSS_TO_STATES_DRAFT.json` ENTRY_11."
    },
    {
      "source_id": "11Q5 (Great Psalms Scroll) — Psalms; J.A. Sanders, DJD IV (Oxford: Clarendon, 1965); MT Ps.4 parallel — verify col/line mapping",
      "link_type": "lexical",
      "state_candidate_id": 10,
      "canonical_ref": "Ps.4.6",
      "rationale": "B-Track DSS: 시편 큐믈란 증거(11Q5)와 MT Ps.4 구절의 어휘·서사 정렬 벤치. A-Track: cosine state 10 앵커 Ps.4.6 — 음성학·트리거 아님."
    },
    {
      "source_id": "11Q5 — Ps.5; DJD IV (Sanders, 1965); liturgical address layer — verify to MT Ps.5.2",
      "link_type": "lexical",
      "state_candidate_id": 11,
      "canonical_ref": "Ps.5.2",
      "rationale": "B-Track DSS: 시편 5장 DSS 평행. A-Track: state 11 앵커 Ps.5.2 — 예배·호소 담론만 병치(벤치)."
    },
    {
      "source_id": "4QDeut — Deuteronomy Qumran witnesses; DJD XIV (E. Ulrich, 1994ff.); Decalogue / theft — verify frag to Deut.5.19",
      "link_type": "lexical",
      "state_candidate_id": 12,
      "canonical_ref": "Deut.5.19",
      "rationale": "B-Track DSS: 신명기 십계·금기 병렬. A-Track: state 12 앵커 Deut.5.19 — 규범 메타만(윤리 트리거 아님)."
    },
    {
      "source_id": "4QGen — Genesis Qumran; Gen.49 Jacob blessings; DJD XII (Oxford: Clarendon); Gad oracle — verify fragment alignment to Gen.49.19",
      "link_type": "thematic",
      "state_candidate_id": 14,
      "canonical_ref": "Gen.49.19",
      "rationale": "B-Track DSS: 창49 족장 축복 서사. A-Track: state 14 앵커 Gen.49.19 — 지리·군사 은유는 벤치 라벨일 뿐 가격 인과 아님."
    },
    {
      "source_id": "Ezra–Nehemiah text-history; 4Q Ezra-type witnesses / LXX Ezra traditions — cross-bench: returnee name-list; verify witness to Ezra.2.54",
      "link_type": "thematic",
      "state_candidate_id": 16,
      "canonical_ref": "Ezra.2.54",
      "rationale": "B-Track DSS/역본: 바벨론 귀환 명단 코호트. A-Track: state 16 앵커 Ezra.2.54 — 인구·스냅샷 메타만 병치(벤치)."
    }
  ]
}
```

**축 구분**: ENTRY_01·05·06·09·10은 DSS 규범·페셔·담론(대부분 `thematic`). ENTRY_02–03은 외경(1에녹, `thematic`). ENTRY_04는 희년서 달력(`temporal`). ENTRY_07–08은 성전 스크롤·오톳 등 **시간·주기 레이어**(`temporal`). **ENTRY_11**은 `analogy_bench`(가설 벤치; NL 관측 메모는 `note`). **ENTRY_12–14**는 정경 앵커와의 `lexical` 정렬 벤치(11Q5 시편, 4QDeut 신명; DJD·단락 매핑은 verify). **ENTRY_15–16**은 `thematic`(4QGen 창49, Ezra–Nehemiah 귀환 명단). 비트코인·실매매 트리거와 무관.

## 평문 엔트리 (NotebookLM 인덱싱용 — 코드펜스 밖)

ENTRY_01 | link_type=thematic | source_id=1QM 1:1-7 (War Scroll, Col.1) | state_candidate_id=1 | corpus=dss | theme=개전·이원론 돌파 가설 | rationale=B-Track DSS: 빛의 아들들 vs 벨리알·키팀·언약 위반자의 개전 서사. A-Track 비유 후보(가설): 극단적 방향성·돌파 국면 — dual_regime·리스크 캡과 무관.

ENTRY_02 | link_type=thematic | source_id=1Enoch 10:4-6 (Charles / Wikisource ch.10) | state_candidate_id=15 | corpus=apocrypha | theme=아자젤·극단 심판 가설 | rationale=B-Track Apocrypha: 아자젤 결박·어둠·대심판의 불. A-Track 비유 후보(가설): 청산·극단 공포(Capitulation) — State 16 후보와 인접 축으로 별도 행 구분 가능.

ENTRY_03 | link_type=thematic | source_id=1Enoch 10:7 (Charles / Wikisource ch.10) | state_candidate_id=2 | corpus=apocrypha | theme=치유·전환 가설 | rationale=B-Track Apocrypha: 타락한 땅의 치유 선포·멸망 방지. A-Track 비유 후보(가설): 심판 국면 이후 질서·반등 서사(V·전환) — 확정 신호 아님.

ENTRY_04 | link_type=temporal | source_id=Jubilees 6:29-38 + 364-day notes (btrack_apocrypha_jubilees_ch6_excerpt_charles.md; btrack_apocrypha_jubilees_calendar_364.md) | state_candidate_id=8 | corpus=pseudepigrapha | theme=364일·주기 질서 가설 | rationale=B-Track Apocrypha: 364일·분기·음력과의 긴장, 정해진 절기 질서. A-Track 비유 후보(가설): 하드코딩된 반감기·주기 신뢰·저변동 인내 — 횡보·매집 담론과 병치 가능.

ENTRY_05 | link_type=thematic | source_id=1QS IX 10-11 (Community Rule; Eng. citation in btrack_dss_1QS_sectarian_context.md) | state_candidate_id=3 | corpus=dss | theme=복수 메시아·규율 공동체 가설 | rationale=B-Track DSS: 예언자와 아론·이스라엘의 기름부음 받은 자에 대한 기대. A-Track 비유 후보(가설): 규율·언약 공동체·장기 신념 — HODL 담론은 비유일 뿐 자동 트리거 금지.

ENTRY_06 | link_type=thematic | source_id=1QpHab (1Q15) col.VII — St.Mark’s I plates + DSS Study Edition (verify col/line) | state_candidate_id=4 | corpus=dss | theme=페셔·위기 재독 | rationale=B-Track DSS: 하바국 해석(페셔)의 ‘위기를 성경으로 재독’ 레이어. A-Track 비유 후보(가설): 규범·도덕 프레임(칠선 언약 맥락)과 시장 서사 병치 — geometry/trigger 아님; Fact-Lock 벤치만.

ENTRY_07 | link_type=temporal | source_id=11QT (11Q19) XLVI–XLVII — Yadin 1977; cf. DJD XXIII (verify col) | state_candidate_id=5 | corpus=dss | theme=성전·절기 규범 | rationale=B-Track DSS: 성전·절기 일정 규범 텍스트. A-Track 대비: Ezra 명단 행은 ‘복귀 코호트’ 스냅샷 — 달력 DSS와 주제만 병치(벤치); 인과·트리거 금지.

ENTRY_08 | link_type=temporal | source_id=4Q319 — DJD XXI Talmon Calendrical Texts (verify sigla) | state_candidate_id=6 | corpus=dss | theme=제사장 주기·신호 | rationale=B-Track DSS: 제사장 주기·신호 표류. A-Track 대비: Nehemiah 복귀자 명단 행 — 인구/재건 흐름과 ‘주기 신호’ 담론만 병치(벤치).

ENTRY_09 | link_type=thematic | source_id=4Q169 (4QpNah) — DJD V Allegro 1968; DSS Study Edition (verify frag/col) | state_candidate_id=7 | corpus=dss | theme=나훔 페셔·악행 귀속 | rationale=B-Track DSS: 나훔 페셔의 악행 귀속·심판 화법. A-Track 대비: 시36 ‘악인의 죄’ 서사와 주제 병치 — 수치/심리 트리거 아님.

ENTRY_10 | link_type=thematic | source_id=CD-A — Charlesworth PTSDSSP 1995; 4Q266–273 DJD XVIII | state_candidate_id=9 | corpus=dss | theme=언약·지경·유배 | rationale=B-Track DSS: 공동체의 언약·지경 담론. A-Track 대비: 여호수아 지파 경계 점과 ‘땅·경계’ 메타만 병치 — 지리≠가격.

ENTRY_11 | link_type=analogy_bench | canonical_ref=1Chr.14.6 | source_id=1QM.1.1 | state_candidate_id=13 | corpus=dss | theme=상전이 벤치([HYPO]) | rationale=[HYPO] 금화교역 상전이 벤치; note=NL v2.1 반증·맥락 오염 요지(SSOT JSON 전문).

ENTRY_12 | link_type=lexical | canonical_ref=Ps.4.6 | source_id=11Q5 DJD IV | state_candidate_id=10 | corpus=dss | theme=시편 DSS·MT 정렬

ENTRY_13 | link_type=lexical | canonical_ref=Ps.5.2 | source_id=11Q5 DJD IV | state_candidate_id=11 | corpus=dss | theme=시편 5장

ENTRY_14 | link_type=lexical | canonical_ref=Deut.5.19 | source_id=4QDeut DJD XIV | state_candidate_id=12 | corpus=dss | theme=신명 십계

ENTRY_15 | link_type=thematic | canonical_ref=Gen.49.19 | source_id=4QGen DJD XII | state_candidate_id=14 | corpus=dss | theme=창49 가드

ENTRY_16 | link_type=thematic | canonical_ref=Ezra.2.54 | source_id=Ezra-Neh witnesses | state_candidate_id=16 | corpus=dss | theme=귀환 명단

공통 경고: disclaimer 필드 — A-Track SSOT 아님; 엔진이 기본 로드 금지; Sefaria/Charles 등은 프록시 표준(정본 아님); 후보(candidate)·벤치만 기록.
