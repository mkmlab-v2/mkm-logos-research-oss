# MKM AI v2 Final Promotion Checklist

목적: `MKM AI Cursor 운영형`에서 `MKM AI v2.0 (Final)`로 승격하기 위한 최소 완료 조건을 고정한다.

## Gate A. MCP Core Profile

- [ ] 워크스페이스 MCP가 코어 8개로 고정됨 (`.cursor/mcp.json`)
- [ ] 금지 서버(`playwright`, `manseryeok-mcp`)가 워크스페이스 프로필에서 제거됨
- [ ] `athena-core`의 `MKM12_LTM_DB_TYPE=file` 확인

## Gate B. Long-Term Memory + NotebookLM Sync

- [ ] `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` 최근 실행 `exit 0`
- [ ] `vault/notebooklm_sources/_LAST_SYNC.txt` UTC 타임스탬프가 최근 7일 이내
- [ ] Vault mirror와 NotebookLM cloud ingest(`source_add`) 분리 운영 원칙 유지

## Gate C. SSOT Consistency

- [ ] `docs/final/CENTRAL_AGENT_MEMORY_V1.md`에 MCP 표준화 이력 존재
- [ ] `docs/final/CENTRAL_AGENT_MEMORY_V1.md`와 실제 `.cursor/mcp.json`이 모순 없음
- [ ] GitHub 최소 공개 정책(`internal` 우선, 예외 시 explicit push)과 문구 정합

## Gate D. Operational Stability

- [ ] 아래 자동 점검 스크립트가 `overall_passed=true` 산출
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_ai_v2_readiness_check.ps1`
- [ ] 산출 아티팩트
  - `docs/final/artifacts/mkm_ai_v2_readiness_latest.json`
- [ ] 최근 7일 PASS 비율 리포트 산출
  - `docs/final/artifacts/mkm_ai_v2_weekly_readiness_report_latest.json`
  - `pass_rate_percent` 기준으로 승격 판단(권장: 95% 이상)

## Gate E. Daily Automation (Recommended)

- [ ] 일일 러너 실행 가능
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmAiV2DailyReadiness.ps1`
- [ ] 스케줄러 등록 완료
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-MkmAiV2ReadinessDailyTask.ps1`
- [ ] 일일 로그 누적 확인
  - `reports/mkm_ai_v2_readiness_log.jsonl`

## Promotion Rule

- 모든 Gate(A~D) 충족 시에만 `MKM AI v2.0 (Final)` 명칭 사용.
- 하나라도 미충족이면 `MKM AI Cursor 운영형` 유지.
- 최종 승격 판정 JSON:
  - `docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json`
  - 생성 명령: `py scripts/check_mkm_ai_v2_promotion_decision.py --workspace-root C:/workspace --min-pass-rate 95 --min-sample-count 3`
- 승격 잠금 아티팩트:
  - `docs/final/artifacts/mkm_ai_v2_final_promotion_lock_latest.json`
