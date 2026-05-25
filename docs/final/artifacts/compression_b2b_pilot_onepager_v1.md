---
schema: compression_b2b_pilot_onepager_v1
tier: B-track Enterprise Pilot
labels: [DRAFT, research_only, publish_allowed=false]
pre_send_gate: scripts/check_compression_enterprise_summary_readiness_v1.py
evidence_paths:
  - docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json
  - docs/final/artifacts/general_compression_kpi_gate_v2.json
policy_pointers:
  - docs/final/COMPRESSION_SLA_POLICY_V1.md
  - docs/final/artifacts/compression_domain_adoption_tier_matrix_v1.json
  - docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md
---

# 다존 라우터 기반 엔터프라이즈 압축 API 제안서

**상태:** `[DRAFT]` · `research_only` · 대외 송출 전 `pre_send_gate` 및 법무 검토 필수.

## 1. 제품 개요

본 API는 무조건적인 자연어 압축 대신, 귀사 데이터의 성격(로그, 텔레메트리, 구조화 JSONL 등)을 실시간 분류하는 다존 라우터(Multi-Zone Router) 엔진입니다. 정해진 비용 정책(Economy Profile) 안에서 토큰 사용량을 최적화하고 하방 위험을 차단하는 데 목적을 둡니다.

- **런타임:** `scripts/core/domain_router.py` · `codebook/shards/zone_*.json` (자동 라우팅; 매 요청 수동 전처리 없음).
- **신규 고객:** PoC 기간(약 2~4주) 샘플 코퍼스·벤치·`must_keep` 튜닝(인간 패키징 공정).

## 2. 기술 검증 실측 데이터 (Evidence)

MKM 내부 동결 벤치 및 품질 게이트 통과 수치는 아래와 같습니다. 수치는 디스크 아티팩트·재현 스크립트로 검증하며, **두 열은 서로 다른 코퍼스·용도**입니다.

| 구분 | 글로벌 토큰 절감률 | 평균 Jaccard (복원 프록시) | SSOT 아티팩트 |
| --- | --- | --- | --- |
| **운영 환경 벤치 (Static Reference)** | **~47.5%** | **~0.890** | `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` |
| **안전 밸브 품질 게이트 (AB Reference)** | **~38.9%** | **~0.996** | `docs/final/artifacts/general_compression_kpi_gate_v2.json` (`decision: GO`) |

**재현(내부):** `py scripts/run_ultra_compression_default.py` · `py scripts/check_general_compression_kpi_gate_v1.py`

**금지:** 위 Reference 수치만으로 AB 게이트 수치를 대체·합선하여 대외 헤드라인에 쓰지 않음 (FAIL-COMP-004 계열).

## 3. 가성비 4단계 온보딩 프로세스 (Scope)

귀사의 실제 상용 트래픽에 본 엔진을 결선하기 전, 리스크 제로 상태에서 아래 순서로 파일럿 패키징을 진행합니다.

1. **[Day 1~7] 샘플 수집:** 귀사 비즈니스의 실제 페이로드 샘플(JSONL 20~50건)을 안전한 격벽 환경에 인입합니다.
2. **[Day 8~14] 샤드 최적화:** 기본 도메인 샤드(`zone_*.json`) 및 선택적 마스터 렉시콘 조인으로 고유어 **must_keep** 규칙을 튜닝합니다(세부 정책 JSON은 비공개; PoC 범위만 제공).
3. **[Day 15~30] 프로필 확정:** 귀사 커스텀 벤치에서 실측 절감률·무결성을 기반으로 과금·SLA 초안을 확정합니다.
4. **[Day 31~90] 유료 파일럿 전환:** 샌드박스 엣지에서 미터링 로그를 관측하며 소액 유료 전환(1~2건)을 집행합니다.

## 4. 이용 한계 및 방화벽 (Limitation)

- **비권장 대상:** 법률 부정문(단일 부정어 판단 핵심), 자유 형식 순수 NL 대화, 실시간 금융 트레이딩 주문 경로 — 본 파일럿 범위 제외 (`compression_domain_adoption_tier_matrix_v1` · `adopt_not_recommended` 정합).
- **무결성 정의:** Jaccard는 **어휘 수준 복원 프록시**이며, LLM 문맥 해석의 100% 동일성을 보증하지 않습니다. 상용 전환 시 **Hydrate Window**로 재검증합니다.
- **Track A·실매매:** 본 파일럿 벤치는 B2B 토큰 절감 엔지니어링용이며, 실매매·예언 승격 레일과 **자동 합선되지 않습니다.**

---

**미터링·SLA 부록 (JSON):** `scripts/build_compression_b2b_pilot_metering_appendix_v1.py` → `docs/final/artifacts/compression_b2b_pilot_metering_appendix_latest.json` (스키마 `docs/final/schemas/compression_b2b_pilot_metering_appendix_v1.schema.json`). 스모크: `scripts/Run-CompressionPilotMeteringSmoke_v1.ps1`.

*교차 참조:* `docs/final/artifacts/compression_public_evidence_pack_skeleton_v1.md` (공개 벤치 패킹 목차 · 동일 수치·면책 정렬).
