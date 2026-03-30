# CROSS_REF Citation Anchor Evidence Checklist (B-Track)

**작성일**: 2026-03-30
**대상 SSOT**: `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json`
**목적**: ENTRY_06~10, ENTRY_12~16의 `loc=...TBD`/`sigla=TBD`를 실제 판본 근거로 치환해 `status=verified_anchor` 단계까지 끌어올린다.

---

## 공통 규칙

- B-track 전용: A-track/실매매/OOF 자동 합선 금지.
- 치환 단위: `source_id`와 `satellite_ref`를 **동일 문자열**로 유지.
- 최소 앵커 포맷: `loc=<col/line/fragment/sigla>` + `refs=<edition>` + `status=verified_anchor`.
- 검증 게이트: `py -m pytest tests/test_cross_ref_dss_schema.py -q --tb=short`.

---

## 작업 대상

| Entry | 현재 상태 | 필요한 증거 | 완료 조건 |
|------|-----------|------------|----------|
| ENTRY_06 (1QpHab) | `line=TBD` | 선택 판본 기준 `col.VII` 정확한 line 범위 | `loc=col.VII, line=<n-m>`로 치환 |
| ENTRY_07 (11QT) | `line=TBD` | `cols.XLVI-XLVII`의 실제 line/segment | `loc=cols.XLVI-XLVII, line=<...>` 치환 |
| ENTRY_08 (4Q319) | `fragment/sigla=TBD` | 공식 fragment sigla + line/plate 매핑 | `loc=frag.<id>, sigla=<...>, line=<...>` |
| ENTRY_09 (4Q169) | `line=TBD` | `frags 3-4 col.ii`의 line anchor | `loc=frags 3-4, col.ii, line=<...>` |
| ENTRY_10 (CD-A/4Q266-273) | `frag/line=TBD` | CD-A I-II 장/행 및 4Q266-273 대응 anchor | `loc=CD-A I-II <line>; 4Q266-273 <frag/line>` |
| ENTRY_12 (11Q5 Ps.4.6) | `col/line=TBD` | 11Q5 witness와 MT Ps.4.6 매핑 line | `loc=...Ps.4.6..., col/line=<...>` |
| ENTRY_13 (11Q5 Ps.5.2) | `col/line=TBD` | 11Q5 witness와 MT Ps.5.2 매핑 line | `loc=...Ps.5.2..., col/line=<...>` |
| ENTRY_14 (4QDeut) | `fragment/line=TBD` | Deut.5.19 대응 fragment/line | `loc=Deut.5.19 frag=<...>, line=<...>` |
| ENTRY_15 (4QGen) | `fragment/line=TBD` | Gen.49.19 대응 fragment/line | `loc=Gen.49.19 frag=<...>, line=<...>` |
| ENTRY_16 (Ezra-Neh witnesses) | `list anchor=TBD` | Ezra.2.54 name-list witness anchor | `loc=Ezra.2.54 list anchor=<...>` |

---

## 실행 순서 (권장)

1. `High` 우선: ENTRY_08, ENTRY_10, ENTRY_14
2. `Med` 우선: ENTRY_06, ENTRY_07, ENTRY_09
3. 나머지 lexical/thematic witness: ENTRY_12, ENTRY_13, ENTRY_15, ENTRY_16
4. 각 배치마다 SSOT 수정 -> `py scripts/sync_btrack_phase3_snapshot_json_fence.py --apply` -> pytest

---

## 완료 판정

- 10개 엔트리 모두 `TBD` 제거
- `status=verified_anchor` 표기
- `tests/test_cross_ref_dss_schema.py` 그린
- `btrack_phase3_cross_ref_snapshot.md` 코드펜스 재동기화 완료
