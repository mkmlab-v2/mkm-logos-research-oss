# Map-Factory PoC v1 — IC 10-Sentence Brief (Fact-Safe)

1. 본 PoC의 목적은 범용 텍스트 압축이 아니라 B2B 반복 문구 도메인에서 무손실 복원과 시뮬레이션 효율을 검증하는 것이다.  
2. 기준 SSOT는 `docs/final/artifacts/comparison_summary_latest.json`이며, 본 문서의 모든 수치는 해당 아티팩트 기준이다.  
3. 배치 무결성은 `integrity_guarantee_flag=true` 및 포함 항목 `decode_check_ok=true`로 확인된다.  
4. KJV/NIV/ESV 교차평가에서 자기 맵 정합 시 `match_rate_by_utf8_octet`는 약 `0.69~0.74`이고 교차 맵은 `0.0`이다.  
5. 다중 도메인(`it_terms`, `finance_terms`, `api_policy`)의 정합 eval 평균은 `aligned_eval_a_avg_match_rate_by_utf8_octet=0.6217916`이다.  
6. 비정합 eval과 KJV 교차 baseline은 각각 `negative_eval_b_all_zero_hit=true`, `kjv_cross_baseline_all_zero_hit=true`로 보고된다.  
7. auto-map 라우팅은 threshold 규칙 하에서 정합 입력은 `map_selected`, 0-hit 입력은 `fallback_verbatim_only`로 분기한다(근거: `auto_map_probe` 섹션).  
8. threshold sweep(`0.01/0.03/0.05/0.1`) 결과, 도메인 정합 3건은 선택 유지, arXiv 비정합 1건은 전 구간 fallback 유지다(`docs/final/artifacts/auto_map_threshold_sweep_latest.json`).  
9. 혼합 문서(api+finance)에서는 single-map 한계로 각 맵 단독 최적만 가능하며 비매칭 구간은 verbatim 처리된다(`mixed_api_finance_probe`).  
10. 본 수치는 `premises` 기반 비트 시뮬레이션 관측값이며, 실제 요금/전송 바이트/VRAM 절감 보장은 별도 계측·계약 조건에서 검증되어야 한다.
