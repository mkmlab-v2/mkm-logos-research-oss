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
| ENTRY_06 (1QpHab) | `partial_anchor_verified (column+line-range)` | col.VII line 1-17 확정 후, canonical(Exod.20.15) 대응 line 정밀화 | `loc=col.VII, line=<n-m>` + 필요 시 `status=verified_anchor` |
| ENTRY_07 (11QT) | `partial_anchor_verified (column-range)` | 공개 소스 line-level 전사 확보(현재 부재) | `loc=cols.XLVI-XLVII, line=<...>` 치환 |
| ENTRY_08 (4Q319) | `partial_anchor_verified (sigla+plates)` | 공개 소스 line 전사 부재 상태에서 fragment별 line anchor 확보 | `loc=frag.<id>, sigla=<...>, line=<...>` |
| ENTRY_09 (4Q169) | `partial_anchor_verified (frag+col+line-range)` | DJD 기준 line crosswalk 직접 대조(현재 QD line-range 확보) | `loc=frags 3-4, col.ii, line=<...>` |
| ENTRY_10 (CD-A/4Q266-273) | `partial_anchor_verified (plates+line)` | CD-A I-II ↔ 4Q266-273 직접 crosswalk line 확정 | `loc=CD-A I-II <line>; 4Q266-273 <frag/line>` |
| ENTRY_12 (11Q5 Ps.4.6) | `partial_anchor_verified (scroll+line-buckets)` | 11Q5 witness와 MT Ps.4.6 **정확 verse line 매핑** | `loc=...Ps.4.6..., line=<...>` + `status=verified_anchor` |
| ENTRY_13 (11Q5 Ps.5.2) | `partial_anchor_verified (scroll+line-buckets)` | 11Q5 witness와 MT Ps.5.2 **정확 verse line 매핑** | `loc=...Ps.5.2..., line=<...>` + `status=verified_anchor` |
| ENTRY_14 (4QDeut) | `partial_anchor_verified (witness-set+plates+line)` | DJD fragment-line crosswalk(정식 표기) 확정 | `loc=Deut.5.19 frag=<...>, line=<...>` |
| ENTRY_15 (4QGen) | `partial_anchor_verified (witness-set+plates+chapter-range)` | Gen.49.19 직접 fragment/line (현재 chapter-range는 49.1-8까지만 확인) | `loc=Gen.49.19 frag=<...>, line=<...>` |
| ENTRY_16 (Ezra-Neh witnesses) | `missing_anchor_until_source_update` (no extant DSS for Ezra.2.54) | 비-DSS witness(LXX/기타) 기준 name-list 대응 anchor 확정 (NL source `c72898ab-...`: 4Q117 extant=Esr 4:2-6, 4:9-11, 5:17, 6:1-6; `21de583e-...` official archive: verse-level extant 미기재/직접 witness 확인 불가) | `loc=Ezra.2.54 list anchor=<...>` |

---

## 실행 순서 (권장, 현재 상태 반영)

1. `유지/검증` 우선: ENTRY_06, ENTRY_09, ENTRY_10, ENTRY_14, ENTRY_15
2. `정밀화` 우선: ENTRY_12, ENTRY_13 (verse-line 직접 매핑)
3. `외부 소스 대기`: ENTRY_07, ENTRY_08, ENTRY_16 (대기 큐 규칙 적용)
4. 변경 배치마다 SSOT 수정 -> `py scripts/sync_btrack_phase3_snapshot_json_fence.py --apply` -> pytest

---

## 외부 판본 대기 큐 (운영 전환)

| Entry | 대기 사유 | 재시도 트리거 | 처리 방식 |
|---|---|---|---|
| ENTRY_07 | 11Q19 `cols.XLVI-XLVII` 공개 line-level 전사 부재 | 공개 전사/신판/DB 업데이트에서 line 제공 | `line=<...>` 갱신 후 `status=verified_anchor` 검토 |
| ENTRY_08 | 4Q319 공개 line 전사 부재(plate/sigla만 확인) | DJD 보강판/공개 전사에서 fragment-line 제공 | `frag/sigla/line` 3요소 정식화 |
| ENTRY_16 | Ezra.2.54 DSS 직접 witness 부재 | 비-DSS witness(LXX/비평판)에서 list anchor 확보 | `missing_anchor` 해제 여부 별도 PR 판단 |

- 운영 규칙: 대기 큐 항목은 **주간 재탐색 금지**, 새 근거 소스가 생긴 경우에만 재시도한다.
- 근거 반영 순서: SSOT JSON -> 스냅샷 fence sync -> `pytest tests/test_cross_ref_dss_schema.py`.
- 점검 주기(권장): 월 1회 또는 소스 업데이트 공지 발생 시 즉시.

### 월간 점검 실행 템플릿

```powershell
Set-Location C:\workspace
powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_waiting_queue_monthly_check.ps1
```

- 빠른 점검(번들 생략):  
  `powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_waiting_queue_monthly_check.ps1 -SkipBundle`
- 운영 권장: 월간 정기 점검은 **번들 포함(기본값)**, 소스 업데이트 직후 1차 확인은 `-SkipBundle` 허용.
- 실행 로그: `docs/final/artifacts/waiting_queue_monthly_check_log.jsonl` 에 JSONL append.

---

## 완료 판정

- 즉시 완료선: 현재 확보 가능한 open-source 근거까지 모두 반영
- 최종 완료선: 대기 큐(ENTRY_07/08/16) 해소 후 `verified_anchor` 승격
- 운영 승인선(ENTRY_16): `decision=promote_proxy_candidate_manual`이면 Direct 부재 사실을 유지한 채 **Proxy 수동승인 종료** 가능
- `tests/test_cross_ref_dss_schema.py` 그린
- `btrack_phase3_cross_ref_snapshot.md` 코드펜스 재동기화 완료

---

## 완료 SOP (외부 소스 업데이트 시 즉시 실행)

### 1) 트리거 확인

- 트리거: 월간 정기 점검일 또는 외부 소스 업데이트 공지 수신
- 대상: `ENTRY_07`, `ENTRY_08`, `ENTRY_16` 우선 재평가

### 2) 증거 수집 기록

- 신규 근거를 `docs/final/artifacts/entry16_source_hunt_log.jsonl` 등 관련 로그에 append
- 원칙: URL/판본/fragment/line/접근 방식(public/private)을 누락 없이 기록

```powershell
# ENTRY_16 신규 소스 1건 추가 + summary/gate 자동 재판정
Set-Location C:\workspace
py scripts/add_entry16_source_and_rejudge.py `
  --source-url "https://example.org/source" `
  --source-title "Example source title" `
  --publisher-or-host "Example host" `
  --resource-type "transcription_line_anchor" `
  --djd-volume "DJD XVI" `
  --page-range "p.291-293" `
  --fragment-sigla "4Q117 frg.1" `
  --line-anchor "frg.1 lines 1-6" `
  --extant-verses-claim "Esr 4:2-6 attested; Esr 2:54 not shown" `
  --witness "no" `
  --evidence-quote "line table confirms Esr 4:2-6 block only" `
  --confidence "med" `
  --access-mode "public"
```

### 3) SSOT 앵커 치환

- 파일: `docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json`
- 필드: `source_id`, `satellite_ref`를 동일 문자열로 갱신
- 목표 포맷: `loc=<...> | refs=<...> | status=verified_anchor`

### 4) 스냅샷 동기화

```powershell
Set-Location C:\workspace
py scripts/sync_btrack_phase3_snapshot_json_fence.py --apply
```

### 5) 게이트 검증

```powershell
Set-Location C:\workspace
py -m pytest tests/test_cross_ref_dss_schema.py -q --tb=short
py -m pytest tests/test_entry16_source_hunt_summary.py tests/test_entry16_promotion_gate.py tests/test_waiting_queue_monthly_check_log.py -q --tb=short
powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_waiting_queue_monthly_check.ps1 -SkipBundle
```

### 6) ENTRY_16 승격 판정

- 파일: `docs/final/artifacts/entry16_promotion_gate.json`
- 판정:
  - `decision=keep_locked` -> 대기 큐 유지
  - `decision=promote_candidate` -> 수동 리뷰 PR로 승격 절차 시작
  - `decision=promote_proxy_candidate_manual` -> 직접 witness 부재를 명시한 Proxy 경로 수동 승인 PR 시작

### 7) 완료 선언 업데이트

- `ENTRY_07/08/16` 모두 `verified_anchor`가 되면 본 체크리스트의 완료 판정을 "최종 완료선 충족"으로 갱신
- 동시에 `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md` 상태를 최종 완료로 동기화

### 운영 Runbook 체크리스트 (스크립트/로그 1:1 대조)

- 콘솔에 `[waiting-queue-check] Running CROSS_REF schema gates...` 출력 확인
- `-SkipBundle` 미사용 시 `[waiting-queue-check] Running full prophecy alignment bundle...` 출력 확인
- `[waiting-queue-check] Generating ENTRY_16 source-hunt summary...` 출력 확인
- `[waiting-queue-check] Evaluating ENTRY_16 promotion gate...` 출력 확인
- 로그 파일 `docs/final/artifacts/waiting_queue_monthly_check_log.jsonl` 최신 행에 아래 키 존재 확인:
  - `checked_at_utc`, `bundle_mode`, `cross_ref_test`, `bundle_test`, `runner`
  - `source_hunt_summary`, `source_hunt_summary_path`
  - `promotion_gate`, `promotion_gate_path`
  - `next_monthly_due_date`, `horizon_t30_date`, `horizon_t90_date`
- 아티팩트 파일 존재 확인:
  - `docs/final/artifacts/entry16_source_hunt_summary.json`
  - `docs/final/artifacts/entry16_promotion_gate.json`

### 완료 잠금 규칙 (반복 작업 중단)

- 아래 둘 다 만족하면 "내부 작업 완료"로 잠금하고 신규 개선 작업을 중단한다.
  - 저장소 검증 번들 그린 유지 (`run_fact_lock_bundle.ps1` 또는 동등)
  - 대기 큐 운영 루프(월간 점검 + 로그 기록) 정상
- 잠금 이후 재개 조건은 **외부 소스 이벤트**로 제한한다.
  - 재개 트리거: `ENTRY_07/08/16` 관련 공개 전사/판본 업데이트 또는 직접 witness 증거 확보
