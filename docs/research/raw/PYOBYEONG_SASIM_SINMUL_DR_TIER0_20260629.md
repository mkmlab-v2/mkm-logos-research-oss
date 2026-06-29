# [TIER0] 동의수세보원 표리병증·사심신물·병증약리 — Commander DR ingest (frozen)

**ingested_at_utc:** 2026-06-29  
**track:** B_TRACK · `[TIER0]` · `research_only` · `send_gate: HOLD`  
**provenance:** 지휘관 제공 Gemini/NL 딥리서치 본문 + MKM 소화 요약 (채팅 ingest)  
**decision_authority:** human_only — **구현 SSOT·임상·CDSS 자동화 아님**

## Ingest contract

- 본 파일은 **날것 아카이브**이다. `[FACT]` 승격은 workspace 정본 행·KCI/OAK·contract만.
- 하위 티어 출처(위키·카페·칼럼·블로그)는 **인용 금지 목록**으로만 보관.
- 엔지니어링 흡수는 `build_ijeoma_pyobyeong_dr_pack_v1.py` → IC-08/09 · LIT_REVIEW v1.1.

## Source tier cleanup (DR 하단 출처 정리)

### Tier A — 핀 가능 `[SECONDARY]` (서지만; 수치 단정은 원문 재검증 전 금지)

| id | 서지 |
|----|------|
| SRC-OAK-ULGWANG | OAK — 소음인체질병증 임상진료지침: 울광병 |
| SRC-KCI-SOYANG-SANGPUNG | KCI — 소양인체질병증 임상진료지침: 소양상풍병 |
| SRC-KCI-SOYANG-MANGEUM | KCI/SciSpace proxy — 소양인 망음병 CPG |
| SRC-ENCYK-ULGWANG | 한국민족문화대백과 — 울광병 |
| SRC-ENCYK-MANGYANG | 한국민족문화대백과 — 망양병 |
| SRC-KCI-PIYUE | KCI — 『동의수세보원』脾約 |
| SRC-DPBIA-SASIM | DBpia — 성명론·사단론·확충론·장부론 통한 사상인 병론 |
| SRC-TOP10-Lee-Song | SciSpace TOP10 #1 Lee & Song 표리병증 역사 |

### Tier B — 교육 참고만 (SSOT 핀 금지)

- 대한한의사협회(akom) 일반 소개, hanitimes 팔강 CPG 개요, hantopic 표준안 연구 요약

### Tier C — **폐기·미인용** (DR에 섞였으나 MKM ingest 제외)

- ko.wikipedia.org, namu.wiki, m.cafe.daum.net, buya.kr 칼럼, mkhealth·egangdong 인터뷰, mjmedi 기고(단독), imaeil 역사칼럼

## DR 핵심 구조 요약 (기계 색인용)

1. **표리 = 노출 축** — 表≈事·身(외부·감각·환경), 裏≈心·物(정서·대인). 사심신물·격치고 `[HYPO]` until primary hanja.
2. **체질별 격벽** — 소음 신수열표열 vs 소양 비수한표한 등 복사 금지.
3. **직교 2D** — 初·中·末(stress/stage) × 표·리(노출); 선형 합성 금지.
4. **병증약리 = Veto/Hold** — 표리동병·표리불해 시 오용 차단; CDSS 자동 처방 아님.
5. **판본 진화** — 갑오→신축 망양: 땀 지표 → 소변 청리/적삽 `[SECONDARY]` until canon line pin.

## Commander DR 원문

> 전문 원문은 채팅 세션에 제공됨(2026-06-29).  
> 구조화·카드화는 `ijeoma_pyobyeong_insight_cards_v1_ablation_latest.json` 및 LIT_REVIEW v1.1이 SSOT.  
> 원문 전문 재동결 필요 시 Vault/NotebookLM export를 본 경로에 append.

## Reproduce

```powershell
cd C:\mkm-sasang-ablation
py scripts/build_ijeoma_pyobyeong_dr_pack_v1.py
```
