---
schema: compression_public_evidence_pack_skeleton_v1
bench_id: MKM-Compression-Bench-v1
tier: B-track Research Skeleton
labels: [DRAFT, research_only, publish_allowed=false]
pre_send_gate: scripts/check_compression_enterprise_summary_readiness_v1.py
planned_builder: scripts/build_compression_public_evidence_pack_v1.py
cross_link: docs/final/artifacts/compression_b2b_pilot_onepager_v1.md
---

# MKM-Compression-Bench-v1 공개 증거 패킹 초안 목차

**상태:** 스켈레톤만 확정. 산출물·익명 코퍼스·`reproduce` 스크립트는 [2단계]에서 `build_compression_public_evidence_pack_v1.py`로 묶음. **언론 송출은 [3단계]** — 1차 유료 PoC + `pre_send_gate` 통과 후.

## 목차 (15항)

1. **벤치마크 메타데이터:** `bench_id`, 버전, `generated_at_utc`, `publish_allowed`.
2. **코퍼스 매니페스트:** 케이스 수, 코퍼스 파일 SHA256, **익명 샘플 10건** 참조 경로(전문 비공개).
3. **운영 환경 참조 벤치 (Reference):** `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` — **~47.5%** / **~0.890**, frozen 조건·bridge OFF 한 줄.
4. **안전 게이트 참조 벤치 (Safety Gate):** `general_compression_kpi_gate_v2.json` — **~38.9%** / **~0.996**, `decision: GO`, AB 코퍼스 용도 명시.
5. **재현 진입점 (Reproducibility):** `run_ultra_compression_default.py`, `check_general_compression_kpi_gate_v1.py`, 래퍼 `reproduce.ps1` / `reproduce.sh` (경로·exit code 계약).
6. **방법론 1p:** `domain_router`, economy cap, Jaccard = 어휘 프록시(의미 % 아님).
7. **실패·경계 케이스:** loss pattern 요약, `sensitive_integrity` 임계(벤치 범위).
8. **비권장 워크로드:** `adopt_not_recommended` 인용 — 자유 NL·법무 부정·트레이딩 핫패스.
9. **IP 격벽:** `zone_*.json` 세부·must_keep 튜닝 로직 **비공개**; 고객 PoC 범위만 최적화.
10. **거버넌스 슬롯:** `publish_allowed`, `pre_send_gate` 결과, 법무 `reviewed_at_utc` 빈 슬롯.
11. **제3자 재현 체크리스트:** 입력 해시 → 스크립트 → 출력 JSON 필드 대조 순서.
12. **제안서 교차 링크:** `compression_b2b_pilot_onepager_v1.md` 수치·면책 정합.
13. **FAIL-COMP-004:** Track A active·실매매·예언 승격과 **자동 합선 없음**.
14. **고객 커스텀 벤치 슬롯:** PoC 후 tenant bench JSONL·실측 필드 예약.
15. **보도자료 면책 3문장 (고정 템플릿):**
    - (1) 수치는 동결 내부 벤치·별도 AB 게이트이며, 귀사 워크로드 실측을 대체하지 않습니다.
    - (2) Jaccard는 어휘 복원 프록시이며 무손실·환각 제거를 단정하지 않습니다.
    - (3) 본 벤치는 토큰 절감 엔지니어링 관측용이며 투자·매매·의료 판단을 제공하지 않습니다.

## 3단계 이정표 (운영)

| 단계 | 시점 | 산출 |
| --- | --- | --- |
| **[1] 기계 고정** | 장전 4+1 클린 (`verify_p0`, KPI gate, pytest 4종) exit 0 | 수치·아티팩트 정합 |
| **[2] 패키지 빌드** | 6~7월 영업 전 | `build_compression_public_evidence_pack_v1.py` + 익명 코퍼스 + reproduce |
| **[3] 대외 송출** | 1차 유료 PoC 후 | 보도자료 + 재현 URL + 면책 3문장 · `readiness` 법무 해제 |
