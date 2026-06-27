# B-Track Phase3 — CROSS_REF_DSS_TO_STATES_DRAFT 송환 스냅샷

**용도**: NotebookLM Phase3 대조 노트 전용. 정본 SSOT는 `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json`(v2). 코드펜스 안은 **SSOT JSON 전문**이며 `py scripts/sync_btrack_phase3_snapshot_json_fence.py --apply`로 갱신한다. 코드펜스 아래 **평문 ENTRY_01–16** 블록은 인덱싱용(필드가 SSOT와 다를 수 있으면 JSON을 따른다).

**SSOT 시각**: `generated_at_utc`는 JSON 상단 값을 따른다(커밋 시각과 별개일 수 있음).

**행 수**: **16행** (ENTRY_01–16) — `LOGOS_STATE_MAPPING_V1`의 `state_id` 1–16 각각 1행; 전문 필드는 항상 SSOT JSON을 따른다.

```json
{
  "schema": "cross_ref_dss_to_states_draft_v2",
  "disclaimer": "B-Track parallel-corpus draft only; not A-Track SSOT; trading engine must not load this path by default. Source standard (proxies, not autographs): bulk apocrypha in-repo uses Sefaria-tagged JSONL (`data/logos/manuscripts/apocrypha_std.jsonl`, per-row `source`). Excerpt MDs may cite R.H. Charles, Charlesworth, Wikisource, or similar. DSS `satellite_ref` lines are thematic alignment notes and do not assert Oxford/DJD diplomatic text unless that edition is explicitly named there. Acquisition of closed-licence critical editions (e.g. DJD) is out of scope for this draft.",
  "generated_at_utc": "2026-03-30T22:00:00+00:00",
  "constitution_ref": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §4.5",
  "canonical_join_ssot": "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json",
  "canonical_join_note": "canonical_ref = verse_id for the same state_id as state_candidate_id (cosine assignment snapshot); not independent thematic exegesis.",
  "entries": [
    {
      "entry_id": "ENTRY_01",
      "canonical_ref": "Lev.21.4",
      "satellite_ref": "1QM 1:1-7 (War Scroll, Col.1)",
      "source_id": "1QM 1:1-7 (War Scroll, Col.1)",
      "corpus_type": "dss",
      "link_type": "thematic",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 1,
      "rationale": "B-Track DSS: 빛의 아들들 vs 벨리알·키팀·언약 위반자의 개전 서사. A-Track 비유 후보(가설): 극단적 방향성·돌파 국면 — dual_regime·리스크 캡과 무관."
    },
    {
      "entry_id": "ENTRY_02",
      "canonical_ref": "Ezra.2.49",
      "satellite_ref": "1Enoch 10:4-6 (Charles / Wikisource ch.10)",
      "source_id": "1Enoch 10:4-6 (Charles / Wikisource ch.10)",
      "corpus_type": "apocrypha",
      "link_type": "thematic",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 15,
      "rationale": "B-Track Apocrypha: 아자젤 결박·어둠·대심판의 불. A-Track 비유 후보(가설): 청산·극단 공포(Capitulation) — State 16 후보와 인접 축으로 별도 행 구분 가능."
    },
    {
      "entry_id": "ENTRY_03",
      "canonical_ref": "1Chr.3.7",
      "satellite_ref": "1Enoch 10:7 (Charles / Wikisource ch.10)",
      "source_id": "1Enoch 10:7 (Charles / Wikisource ch.10)",
      "corpus_type": "apocrypha",
      "link_type": "thematic",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 2,
      "rationale": "B-Track Apocrypha: 타락한 땅의 치유 선포·멸망 방지. A-Track 비유 후보(가설): 심판 국면 이후 질서·반등 서사(V·전환) — 확정 신호 아님."
    },
    {
      "entry_id": "ENTRY_04",
      "canonical_ref": "1Chr.8.31",
      "satellite_ref": "Jubilees 6:29-38 + 364-day notes (btrack_apocrypha_jubilees_ch6_excerpt_charles.md; btrack_apocrypha_jubilees_calendar_364.md)",
      "source_id": "Jubilees 6:29-38 + 364-day notes (btrack_apocrypha_jubilees_ch6_excerpt_charles.md; btrack_apocrypha_jubilees_calendar_364.md)",
      "corpus_type": "pseudepigrapha",
      "link_type": "temporal",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 8,
      "rationale": "B-Track Apocrypha: 364일·분기·음력과의 긴장, 정해진 절기 질서. A-Track 비유 후보(가설): 하드코딩된 반감기·주기 신뢰·저변동 인내 — 횡보·매집 담론과 병치 가능."
    },
    {
      "entry_id": "ENTRY_05",
      "canonical_ref": "Ps.27.10",
      "satellite_ref": "1QS IX 10-11 (Community Rule; Eng. citation in btrack_dss_1QS_sectarian_context.md)",
      "source_id": "1QS IX 10-11 (Community Rule; Eng. citation in btrack_dss_1QS_sectarian_context.md)",
      "corpus_type": "dss",
      "link_type": "thematic",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 3,
      "rationale": "B-Track DSS: 예언자와 아론·이스라엘의 기름부음 받은 자에 대한 기대. A-Track 비유 후보(가설): 규율·언약 공동체·장기 신념 — HODL 담론은 비유일 뿐 자동 트리거 금지."
    },
    {
      "entry_id": "ENTRY_06",
      "canonical_ref": "Exod.20.15",
      "satellite_ref": "1QpHab (1Q15) | loc=col.VII, line=1-17 (Qumran-Digital transcription table) | refs=St.Mark's I (ASOR 1950), DSS Study Edition (Brill), Qumran-Digital 1QpHab transcription (2024-04-29) | status=partial_anchor_verified (column+line-range)",
      "source_id": "1QpHab (1Q15) | loc=col.VII, line=1-17 (Qumran-Digital transcription table) | refs=St.Mark's I (ASOR 1950), DSS Study Edition (Brill), Qumran-Digital 1QpHab transcription (2024-04-29) | status=partial_anchor_verified (column+line-range)",
      "corpus_type": "dss",
      "link_type": "thematic",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 4,
      "rationale": "B-Track DSS: 하바국 해석(페셔)의 ‘위기를 성경으로 재독’ 레이어. A-Track 비유 후보(가설): 규범·도덕 프레임(칠선 언약 맥락)과 시장 서사 병치 — geometry/trigger 아님; Fact-Lock 벤치만."
    },
    {
      "entry_id": "ENTRY_07",
      "canonical_ref": "Ezra.2.45",
      "satellite_ref": "11QT (11Q19) | loc=cols.XLVI-XLVII, line=TBD (public line-level transcription unavailable in consulted open sources) | refs=Yadin 1977-1983 (11Q19 primary); DJD XXIII (11Q20-31, Temple b/c comparanda) | status=partial_anchor_verified (column-range)",
      "source_id": "11QT (11Q19) | loc=cols.XLVI-XLVII, line=TBD (public line-level transcription unavailable in consulted open sources) | refs=Yadin 1977-1983 (11Q19 primary); DJD XXIII (11Q20-31, Temple b/c comparanda) | status=partial_anchor_verified (column-range)",
      "corpus_type": "dss",
      "link_type": "temporal",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 5,
      "rationale": "B-Track DSS: 성전·절기 일정 규범 텍스트. A-Track 대비: Ezra 명단 행은 ‘복귀 코호트’ 스냅샷 — 달력 DSS와 주제만 병치(벤치); 인과·트리거 금지.",
      "note": "Bench policy: temporal(성전/절기) 후보. 승격 조건=11Q19 cols.XLVI-XLVII의 공개 line 전사 확보 + Ezra.2.45와의 병치 규칙 유지. 반증 훅=절기 규범을 복귀 명단의 직접 인과로 해석하는 경우. Local evidence (2026-03-30): consulted open sources에서 column 표기(XLVI-XLVII)는 확인되나 line-level 전사는 확인되지 않아 line anchor는 TBD 유지."
    },
    {
      "entry_id": "ENTRY_08",
      "canonical_ref": "Neh.7.56",
      "satellite_ref": "4Q319 (4QOtot) | loc=fragment/sigla=4QOtot, plate=Pls X-XIII, line=TBD (public line transcription unavailable in consulted open sources) | refs=DJD XXI (Talmon et al. 2001), IAA 4Q319 archive page | status=partial_anchor_verified (sigla+plates)",
      "source_id": "4Q319 (4QOtot) | loc=fragment/sigla=4QOtot, plate=Pls X-XIII, line=TBD (public line transcription unavailable in consulted open sources) | refs=DJD XXI (Talmon et al. 2001), IAA 4Q319 archive page | status=partial_anchor_verified (sigla+plates)",
      "corpus_type": "dss",
      "link_type": "temporal",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 6,
      "rationale": "B-Track DSS: 제사장 주기·신호 표류. A-Track 대비: Nehemiah 복귀자 명단 행 — 인구/재건 흐름과 ‘주기 신호’ 담론만 병치(벤치).",
      "note": "Bench policy: temporal(주기/신호) 후보. 승격 조건=4Q319 fragment별 line anchor 확보 + Neh.7.56 명단형 메타와의 병치 규칙 유지. 반증 훅=달력 표식을 직접 인과 트리거로 오독하는 경우. Local evidence (2026-03-30): DJD XXI에서 4QOtot의 plate 범위(Pls X-XIII) 확인, IAA 공개 아카이브 페이지에서는 line 전사가 제공되지 않아 line anchor는 TBD 유지."
    },
    {
      "entry_id": "ENTRY_09",
      "canonical_ref": "Ps.36.1",
      "satellite_ref": "4Q169 (4QpNah) | loc=frags 3-4, col.ii, line=1-12 | refs=DJD V (Allegro 1968), DSS Study Edition (Brill), Qumran-Digital 4Q169 transcription (2025-03-11) | status=partial_anchor_verified (frag+col+line-range)",
      "source_id": "4Q169 (4QpNah) | loc=frags 3-4, col.ii, line=1-12 | refs=DJD V (Allegro 1968), DSS Study Edition (Brill), Qumran-Digital 4Q169 transcription (2025-03-11) | status=partial_anchor_verified (frag+col+line-range)",
      "corpus_type": "dss",
      "link_type": "thematic",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 7,
      "rationale": "B-Track DSS: 나훔 페셔의 악행 귀속·심판 화법. A-Track 대비: 시36 ‘악인의 죄’ 서사와 주제 병치 — 수치/심리 트리거 아님.",
      "note": "Bench policy: thematic(심판/악행 귀속) 후보. 승격 조건=DJD 표기 기준 line crosswalk의 직접 대조 완료. 반증 훅=페셔 정치-역사 문맥을 시편 심리 문맥과 직접 동일시하는 경우. Local evidence (2026-03-30): Qumran-Digital 4Q169 전사에서 frgs 3-4 col.ii line 1-12 연속 구간 확인."
    },
    {
      "entry_id": "ENTRY_10",
      "canonical_ref": "Josh.15.22",
      "satellite_ref": "CD-A I-II (+4Q266-273) | loc=4QDamascus Document witnesses -> DJD XVIII plates I–XLII; 4Q267 frg.2 line 4 attests boundary-language (מסיגי גבול), but direct CD-A I-II line crosswalk remains TBD | refs=Charlesworth PTSDSSP 1995, DJD XVIII (Baumgarten 1996), Qumran-Digital 4Q267 transcription (2023-10-25) | status=partial_anchor_verified (plates+line)",
      "source_id": "CD-A I-II (+4Q266-273) | loc=4QDamascus Document witnesses -> DJD XVIII plates I–XLII; 4Q267 frg.2 line 4 attests boundary-language (מסיגי גבול), but direct CD-A I-II line crosswalk remains TBD | refs=Charlesworth PTSDSSP 1995, DJD XVIII (Baumgarten 1996), Qumran-Digital 4Q267 transcription (2023-10-25) | status=partial_anchor_verified (plates+line)",
      "corpus_type": "dss",
      "link_type": "thematic",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 9,
      "rationale": "B-Track DSS: 공동체의 언약·지경 담론. A-Track 대비: 여호수아 지파 경계 점과 ‘땅·경계’ 메타만 병치 — 지리≠가격.",
      "note": "Bench policy: thematic(경계/지경) 후보. 승격 조건=CD-A I-II와 4Q266-273의 직접 line crosswalk 확보. 반증 훅=경계 어휘가 일반 도덕 문맥으로만 남아 Josh.15.22 지경 메타와 구조 정합이 약해지는 경우. Local evidence (2026-03-30): Qumran-Digital 4Q267 frg.2 line 4에서 'מסיגי גבול' 확인되어 line evidence는 partial 반영, CD-A I-II 직결 line은 미확정."
    },
    {
      "entry_id": "ENTRY_11",
      "canonical_ref": "1Chr.14.6",
      "satellite_ref": "1QM.1.1",
      "source_id": "1QM.1.1",
      "corpus_type": "dss",
      "link_type": "analogy_bench",
      "confidence": 0.82,
      "artifact_path": "docs/final/btrack_phase3_cross_ref_snapshot.md",
      "state_candidate_id": 13,
      "rationale": "[HYPO] 금화교역(金火交易) 상전이 벤치: 1Chr.14.6의 '상태'를 에스겔 1:4의 불꽃 환상 및 1QM의 에너지 충돌 서사와 구조적으로 연결. 학계의 비평을 넘어선 '상태 함수' 대칭성 실험용.",
      "note": "NL v2.1 cross_notebook_query (Apocrypha/DSS/Phase3, 3/3): 관측 요지 — 정렬은 가능하나 반증으로 (1) 희년서 364일 논지의 분리주의·정치 동기 가능성, (2) DSS/히브리 원어에 금화교역 상응 형이상학 어휘 부재, (3) 1Chr.14.6 행정·연대기 맥락과 묵시 텍스트 병치 시 False equivalence 위험. 주요 취약점: 맥락 오염(Context contamination)·제2성전기 이원론 vs 동양 순환 은유의 존재론적 비호환. [HYPO] 승격 보류; A-track·실매매·OOF 자동 합선 금지. NL 2026-03-30 notebook_query 보강: (a) 반증 3종 분류=맥락 오염/존재론적 동치 오류/숫자 은유, (b) 인용 정밀도 감사=1QpHab·11QT(Med), 4Q319·CD-A(High), 열·행·fragment/sigla 보강 필요. Source: 5a0ac312-d9a1-4065-82c1-49455ad0a420 (btrack_phase3_cross_ref_snapshot.md)."
    },
    {
      "entry_id": "ENTRY_12",
      "canonical_ref": "Ps.4.6",
      "satellite_ref": "MT | loc=none (no Qumran Hebrew witness for Ps.4.6 in ETCBC/local scan) | refs=BHS/MT | status=mt_only_no_qumran_witness | prior_bench=11Q5(hypothesis_retired)",
      "source_id": "MT | loc=none (no Qumran Hebrew witness for Ps.4.6 in ETCBC/local scan) | refs=BHS/MT | status=mt_only_no_qumran_witness | prior_bench=11Q5(hypothesis_retired)",
      "corpus_type": "mt",
      "link_type": "lexical",
      "confidence": null,
      "artifact_path": "reports/cross_ref_entry_12_13_evidence_sidecar_v1_latest.json",
      "state_candidate_id": 10,
      "rationale": "B-Track: MT-only bench after 11Q5 retirement. A-Track state 10 anchor Ps.4.6 — non-gating.",
      "note": "P5/P8 update: 11Q5 bench retired (scroll Psalms 101+); no DSS line witness for Ps.4.6. canonical_ref Ps.4.6 retained for A-track state-10 bench label only. verified_anchor not claimed."
    },
    {
      "entry_id": "ENTRY_13",
      "canonical_ref": "Ps.5.2",
      "satellite_ref": "4Q98b | loc=frg.1 line 1; shadow_verse_anchor=Ps.5.8-9 (bench canonical_ref Ps.5.2; MT v.2 direct line not verified) | refs=Ulrich et al., DJD XVI (4QPss); Qumran-Digital 4Q98b 2025-03-11 | witness_id=dss_etcbc_line_1601488 | status=commander_verified_shadow_witness | prior_bench=11Q5(retired)",
      "source_id": "4Q98b | loc=frg.1 line 1; shadow_verse_anchor=Ps.5.8-9 (bench canonical_ref Ps.5.2; MT v.2 direct line not verified) | refs=Ulrich et al., DJD XVI (4QPss); Qumran-Digital 4Q98b 2025-03-11 | witness_id=dss_etcbc_line_1601488 | status=commander_verified_shadow_witness | prior_bench=11Q5(retired)",
      "corpus_type": "dss",
      "link_type": "lexical",
      "confidence": null,
      "artifact_path": "reports/shadow_4q_ps5_witness_registry_v1_latest.json",
      "state_candidate_id": 11,
      "rationale": "B-Track DSS shadow rail: 4Q98b commander-verified witness. A-Track state 11 bench Ps.5.2 — non-gating.",
      "note": "P7 commander promotion: 4Q98b frg.1 line 1 shadow witness for Ps 5:8-9 per DJD/QD. CROSS_REF canonical_ref stays Ps.5.2 (A-track state-11 bench). mt_ps_5_2_crosswalk_gap remains true; verified_anchor not claimed."
    },
    {
      "entry_id": "ENTRY_14",
      "canonical_ref": "Deut.5.19",
      "satellite_ref": "4QDeut (a-q) | loc=DJD XIV Deuteronomy witnesses (Pls I-XXXI); 4Q129 frg.1R line 9 preserves Decalogue sequence incl. Deut.5.19 (לא תגנוב); direct DJD fragment-line crosswalk remains TBD | refs=DJD XIV (Ulrich et al. 1995), Qumran-Digital 4Q129 transcription (2024-07-30) | status=partial_anchor_verified (witness-set+plates+line)",
      "source_id": "4QDeut (a-q) | loc=DJD XIV Deuteronomy witnesses (Pls I-XXXI); 4Q129 frg.1R line 9 preserves Decalogue sequence incl. Deut.5.19 (לא תגנוב); direct DJD fragment-line crosswalk remains TBD | refs=DJD XIV (Ulrich et al. 1995), Qumran-Digital 4Q129 transcription (2024-07-30) | status=partial_anchor_verified (witness-set+plates+line)",
      "corpus_type": "dss",
      "link_type": "lexical",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 12,
      "rationale": "B-Track DSS: 신명기 십계·금기 병렬. A-Track: state 12 앵커 Deut.5.19 — 규범 메타만(윤리 트리거 아님).",
      "note": "Bench policy: lexical/규범 정렬 후보. 승격 조건=4QDeut fragment가 Deut.5.19 금기 문맥에 직접 대응. 반증 훅=fragment 위치 불확정 또는 십계 일반 규범으로만 남는 경우. NL notebook_query(2026-03-30, conv 46c6c47a): witness 정합도 M/L, verify 전 단계로 승격 보류. NL cross_notebook_query(2026-03-30): DSS-only/Fusion/Phase3 전부에서 fragment/sigla anchor 부재 확인. Local evidence (2026-03-30): Qumran-Digital 4Q129 전사에서 frg.1R line 9에 Decalogue 구문(לא תרצח/לא תנאף/לא תגנוב)이 확인되어 Deut.5.19 line anchor를 partial로 상향."
    },
    {
      "entry_id": "ENTRY_15",
      "canonical_ref": "Gen.49.19",
      "satellite_ref": "4QGen (b-k) | loc=DJD XII Genesis witnesses (Pls VI-XIII); chapter witness confirms Gen.49.1-8 (4Q1/4Q5), but Gen.49.19 direct fragment/line remains TBD | refs=DJD XII (Ulrich et al. 1994), DSSEnglishBible Gen49 page | status=partial_anchor_verified (witness-set+plates+chapter-range)",
      "source_id": "4QGen (b-k) | loc=DJD XII Genesis witnesses (Pls VI-XIII); chapter witness confirms Gen.49.1-8 (4Q1/4Q5), but Gen.49.19 direct fragment/line remains TBD | refs=DJD XII (Ulrich et al. 1994), DSSEnglishBible Gen49 page | status=partial_anchor_verified (witness-set+plates+chapter-range)",
      "corpus_type": "dss",
      "link_type": "thematic",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 14,
      "rationale": "B-Track DSS: 창49 족장 축복 서사. A-Track: state 14 앵커 Gen.49.19 — 지리·군사 은유는 벤치 라벨일 뿐 가격 인과 아님.",
      "note": "Bench policy: thematic 후보. 승격 조건=4QGen witness에서 Gad oracle 대응 구간 확인 + 은유를 상태 메타로만 제한. 반증 훅=군사/지리 비유를 실증 인과로 오독하는 경우. NL notebook_query(2026-03-30, conv 46c6c47a): witness 정합도 M/L, false equivalence 경고로 승격 보류. NL cross_notebook_query(2026-03-30): DSS-only/Fusion/Phase3 전부에서 fragment/col-line 'missing anchor' 확인. Local evidence (2026-03-30): 공개 전사/번역 집계에서 Gen.49는 4Q1/4Q5 기준 49.1-8까지만 확인되어 Gen.49.19 직접 witness는 미확정."
    },
    {
      "entry_id": "ENTRY_16",
      "canonical_ref": "Ezra.2.54",
      "satellite_ref": "Ezra-Neh witnesses | loc=no extant DSS witness for Ezra.2.54 list (4Q117 attests Esr 4:2-6, 4:9-11, 5:17, 6:1-6 only); non-DSS LXX witness anchors Ezra 2:54 at verse/chapter level (manual review candidate) | refs=Qumran-Digital 4Q117 transcription (2024-07-30), BlueLetterBible LXX Ezra 2:54, BibleHub Swete LXX Ezra 2 | status=missing_anchor_until_source_update",
      "source_id": "Ezra-Neh witnesses | loc=no extant DSS witness for Ezra.2.54 list (4Q117 attests Esr 4:2-6, 4:9-11, 5:17, 6:1-6 only); non-DSS LXX witness anchors Ezra 2:54 at verse/chapter level (manual review candidate) | refs=Qumran-Digital 4Q117 transcription (2024-07-30), BlueLetterBible LXX Ezra 2:54, BibleHub Swete LXX Ezra 2 | status=missing_anchor_until_source_update",
      "corpus_type": "dss",
      "link_type": "thematic",
      "confidence": null,
      "artifact_path": null,
      "state_candidate_id": 16,
      "rationale": "B-Track DSS/역본: 바벨론 귀환 명단 코호트. A-Track: state 16 앵커 Ezra.2.54 — 인구·스냅샷 메타만 병치(벤치).",
      "note": "Bench policy: thematic(코호트 스냅샷) 후보. 승격 조건=Ezra-Nehemiah witness 계열에서 이름목록/귀환 코호트 대응 확인. 반증 훅=텍스트 전승 불확정으로 witness 연결이 붕괴하는 경우. NL notebook_query(2026-03-30, conv 46c6c47a): witness 정합도 M/L, false equivalence 경고로 승격 보류. NL cross_notebook_query(2026-03-30): DSS-only/Fusion/Phase3 전부에서 witness anchor 'missing' 확인. Local evidence (2026-03-30): data/etcbc-dss/log/align-*.txt에서 `Ezra`는 일부 `4Q117`(주로 Ezra 4–6)로 매핑 확인되었으나, `Ezra', '2'` 또는 Ezra 2(=ch.2) 매핑은 전 파일에서 미탐지. NL notebook_query(2026-03-30, source=c72898ab-b0b2-4875-a856-59c39a166875): 4Q117 extant = Esr 4:2-6, 4:9-11, 5:17, 6:1-6; Ezra 2:54 direct witness = No. NL notebook_query(2026-03-30, source=21de583e-bfc2-4294-9e25-7a1678f624c2 official archive): fragment/plate 메타만 제공되고 verse-level extant 범위는 미기재, Ezra 2:54 direct witness 확인 불가(No). Manual gate refresh (2026-03-31): entry16_promotion_gate decision=promote_candidate, has_direct_witness=true, witness_yes_count=3, status=candidate_ready_for_manual_review. 운영 해석: DSS direct 부재 Fact는 유지하고, 비-DSS LXX witness를 보조 앵커로 승격 후보(manual review) 상태로 관리."
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

ENTRY_06 | link_type=thematic | source_id=1QpHab (1Q15) | loc=col.VII, line=TBD | refs=St.Mark's I (ASOR 1950), DSS Study Edition (Brill) | status=partial_anchor_verified (column) | state_candidate_id=4 | corpus=dss | theme=페셔·위기 재독 | rationale=B-Track DSS: 하바국 해석(페셔)의 ‘위기를 성경으로 재독’ 레이어. A-Track 비유 후보(가설): 규범·도덕 프레임(칠선 언약 맥락)과 시장 서사 병치 — geometry/trigger 아님; Fact-Lock 벤치만.

ENTRY_07 | link_type=temporal | source_id=11QT (11Q19) | loc=cols.XLVI-XLVII, line=TBD | refs=Yadin 1977, DJD XXIII | status=partial_anchor_verified (column-range) | state_candidate_id=5 | corpus=dss | theme=성전·절기 규범 | rationale=B-Track DSS: 성전·절기 일정 규범 텍스트. A-Track 대비: Ezra 명단 행은 ‘복귀 코호트’ 스냅샷 — 달력 DSS와 주제만 병치(벤치); 인과·트리거 금지.

ENTRY_08 | link_type=temporal | source_id=4Q319 (4QOtot) | loc=fragment/sigla=4QOtot, plate=Pls X-XIII, line=TBD | refs=DJD XXI (Talmon et al. 2001) | status=partial_anchor_verified (sigla+plates) | state_candidate_id=6 | corpus=dss | theme=제사장 주기·신호 | rationale=B-Track DSS: 제사장 주기·신호 표류. A-Track 대비: Nehemiah 복귀자 명단 행 — 인구/재건 흐름과 ‘주기 신호’ 담론만 병치(벤치).

ENTRY_09 | link_type=thematic | source_id=4Q169 (4QpNah) | loc=frags 3-4, col.ii, line=TBD | refs=DJD V (Allegro 1968), DSS Study Edition (Brill) | status=partial_anchor_verified (frag+col) | state_candidate_id=7 | corpus=dss | theme=나훔 페셔·악행 귀속 | rationale=B-Track DSS: 나훔 페셔의 악행 귀속·심판 화법. A-Track 대비: 시36 ‘악인의 죄’ 서사와 주제 병치 — 수치/심리 트리거 아님.

ENTRY_10 | link_type=thematic | source_id=CD-A I-II (+4Q266-273) | loc=4QDamascus Document (4Q266-273) witnesses -> DJD XVIII plates I–XLII; mapping to CD-A ch. I-II line anchor remains TBD | refs=Charlesworth PTSDSSP 1995, DJD XVIII (Baumgarten 1996) | status=partial_anchor_verified (plates) | state_candidate_id=9 | corpus=dss | theme=언약·지경·유배 | rationale=B-Track DSS: 공동체의 언약·지경 담론. A-Track 대비: 여호수아 지파 경계 점과 ‘땅·경계’ 메타만 병치 — 지리≠가격.

ENTRY_11 | link_type=analogy_bench | canonical_ref=1Chr.14.6 | source_id=1QM.1.1 | state_candidate_id=13 | corpus=dss | theme=상전이 벤치([HYPO]) | rationale=[HYPO] 금화교역 상전이 벤치; note=NL v2.1 반증·맥락 오염 요지(SSOT JSON 전문).

ENTRY_12 | link_type=lexical | canonical_ref=Ps.4.6 | source_id=11Q5 | loc=Psalm witness -> MT Ps.4.6, col/line=TBD | refs=DJD IV (Sanders 1965) | status=missing_anchor_until_source_update | state_candidate_id=10 | corpus=dss | theme=시편 DSS·MT 정렬

ENTRY_13 | link_type=lexical | canonical_ref=Ps.5.2 | source_id=11Q5 | loc=Psalm witness -> MT Ps.5.2, col/line=TBD | refs=DJD IV (Sanders 1965) | status=missing_anchor_until_source_update | state_candidate_id=11 | corpus=dss | theme=시편 5장

ENTRY_14 | link_type=lexical | canonical_ref=Deut.5.19 | source_id=4QDeut (a-q) | loc=DJD XIV Deuteronomy witnesses (Pls I-XXXI); Deut.5.19 fragment/line remains TBD | refs=DJD XIV (Ulrich et al. 1995) | status=partial_anchor_verified (witness-set+plates) | state_candidate_id=12 | corpus=dss | theme=신명 십계

ENTRY_15 | link_type=thematic | canonical_ref=Gen.49.19 | source_id=4QGen (b-k) | loc=DJD XII Genesis witnesses (Pls VI-XIII); Gen.49.19 fragment/line remains TBD | refs=DJD XII (Ulrich et al. 1994) | status=partial_anchor_verified (witness-set+plates) | state_candidate_id=14 | corpus=dss | theme=창49 가드

ENTRY_16 | link_type=thematic | canonical_ref=Ezra.2.54 | source_id=Ezra-Neh witnesses | loc=Ezra.2.54 list anchor=TBD | refs=4Q Ezra-type + LXX Ezra traditions | status=missing_anchor_until_source_update | state_candidate_id=16 | corpus=dss | theme=귀환 명단

공통 경고: disclaimer 필드 — A-Track SSOT 아님; 엔진이 기본 로드 금지; Sefaria/Charles 등은 프록시 표준(정본 아님); 후보(candidate)·벤치만 기록.

---

## 문서 라벨 규칙 (Fact-Safe)

| 라벨 | 의미 | 사용 기준 |
|------|------|-----------|
| `[FACT]` | SSOT·검증 가능 진술 | `artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json` 및 명명된 판본·판면 참조와 일치 |
| `[HYPO]` | 테마 정렬·A-Track 비유 후보 | JSON `rationale`, ENTRY 평문의 **가설** 문구; 자동 트리거 아님 |
| `[VISION]` | 전략·로드맵 문장 | Phase3 인덱싱·벤치 목표; 본선 결정으로 단정 금지 |
| `[NON-MEDICAL]` | 비의료 고지 | 건강·체질 관련 문구 포함 시 필수 |

### 수치·연대 표기 (Tier 1 재사용)

학술 수치를 인용할 때는 `출처 + 셋 구성 + 지표 정의`를 한 줄에 함께 쓴다(본 스냅샷의 DSS–정경 병치 행과 별개).
