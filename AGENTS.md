# AGENTS — 워크스페이스 에이전트 SSOT (주입층 · slim)

**역할**: Cursor **매 턴 주입**용 짧은 진입점. 페르소나 전체 표·도메인·압축·B-track 상세 → **`docs/final/AGENTS_REFERENCE_V1.md`** (`@` 또는 Read).

## 우선순위 (충돌 시 위가 이김)

1. 루트 `.cursorrules` (TITAN · Ask Gate)
2. `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` + 호출 가능 `.py`/스크립트·exit code·아티팩트
3. `.cursor/rules/*.mdc` 코어 `alwaysApply` (감사: `py scripts/check_cursor_rules_context_diet_v1.py --strict`)
4. 본 파일 · 확장 `docs/final/AGENTS_REFERENCE_V1.md`

## Fact-Lock · 격벽 (한 화면)

- 구현·통과 주장 = CONSTITUTION + 스크립트·pytest만. NL·채팅 요약 단독 근거 금지.
- Track A(운영) vs B(연구/`[HYPO]`) — **B→A·실매매 자동 합선 금지**.
- **솔로 OSS (전 레인 기본):** MIT+README+secret check · counsel/변호사 **지휘관 명시 시만** — `mkm_solo_oss_release_policy_v1_latest.json`.
- 렌즈: `사상` / `명리` / `성경(Logos)` — Final Action = 1차 `regime_map` + 운영 게이트.
- **렌즈 활용 SSOT:** `docs/final/LENS_UTILIZATION_CHARTER_V1.md` (도메인 매트릭스·위임·ablation).
- MKM = **4AI core + Absolute Balance Coordinator Mode** (제5 AI/체질 아님) · Shallow=ops pin+LTM · Deep=anchor≤3 · inject=trust/`semantic_rag_bridge_insight_bundle` · 4D `S-L-K-M` · 상세 `INTERNAL_SEMANTIC_RAG_4D_ARCH_OUTLINE_V1.md`.

## 재개 · 종료 (SSOT: `.cursor/rules/central-agent-memory.mdc`)

| 트리거 | 동작 |
|--------|------|
| 장기기억 맥락이어 · 미션로그 이어서 · CENTRAL 기준 (동등) | `powershell -File scripts\Invoke-MkmCursorSessionUpgrade_v1.ps1` (`-Lane` 있으면) → Read `docs/final/artifacts/mkm_chat_resume_pack_latest.md` — **MISSION_LOG 통째 금지** |
| **개발 세션 (마찰↓·상식)** | **지휘관 env 불필요** · 구현/위임 채팅=에이전트 soft 자동 · 공식 「장기기억 맥락이어」만 OPS hard · SSOT `mkm_dev_session_resume_profile_v1.json` v2 — Fact-Lock/SEND 유지 |
| **장기기억 맥락이어 고급해석** | `…Invoke-MkmCursorSessionUpgrade_v1.ps1 -Lane oracle -ResumeMode AdvancedLogos` → resume pack · `[HYPO]` why 단답·SEND·Track A 금지 · `mkm_commander_resume_triggers_v1.json` |
| **마무리 · 마무리해줘** | `run_mkm_cursor_session_end_v1.py` (`--lane`·`--continuity-id`·한 줄) — alias `장기기억 저장` · `체크포인트` |
| Pillar A 주간 회귀 (Infra) | `run_workspace_automation_health.ps1 -PillarACursorContinuitySmokeOnly` |
| 의미 있는 진행 후 | `MISSION_LOG.md` **해당 레인** 다음 Action **1줄**만 (`mission-log-combat-ssot.mdc`) |

- **solo_ops / WSE-3:** 재개 시 solo_ops `last_ok` 확인(`mkm-solo-background-ops-auto.mdc`) · 스타터 `@mkm-wse3-commander-starters.mdc`

## 페르소나 트리거 (요약 — 전체 표는 REFERENCE)

| 구분자 | 명령 (루트 `C:\workspace`) |
|--------|------------------------------|
| 【아테나 점검】 | `powershell -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle` |
| 【아테나 UMR 신뢰성】 | `… -Persona AthenaUniversalMultiResReliability` |
| 【빠른 헌법 점검】 | `… -Persona P0` |
| 【암행어사 점검】 | `… -Persona AmsaengHealth` |
| 【암행어사 UMR 신뢰성】 | `… -Persona AmsaengUniversalMultiResReliability` |
| **【자율점검】** · `자율루프` · `오늘 자율루프` | `… -Persona AutonomousPatrol` → `reports/mkm_autonomous_patrol_latest.json` · 계약 `mkm_autonomous_patrol_commander_daily_contract_v1_latest.md` · ≠AthenaBundle daily · `@.cursor/skills/mkm-autonomous-patrol/SKILL.md` |
| 【커서 세션 업그레이드】 | `… -Persona CursorSessionUpgrade` |
| 【고차원 자율진화】 | `… -Persona HdAutonomousEvolution` (env `MKM_HD_AE_MISSION`·`MKM_HD_AE_LANE`; SSOT `docs/final/artifacts/mkm_high_dimensional_autonomous_evolution_v1_latest.json`) |
| 【Bounded lane shadow】 | `… -Persona BoundedLaneLoopShadow` |
| 【사상 스택/마스터/P9–P16】 | `… -Persona SasangRailStack|Master|P9…P16` — 상세 REFERENCE |
| **【사상 작업 시작】** · 사상 레인 work-start | UMR sasang + read_order + bundle HOLD + unified `_latest` · `@.cursor/skills/mkm-sasang-lane-ops/SKILL.md` · `@mkm-universal-multi-res-router-sasang-v1` |
| 【에이전트 micro-loop】 | `… -Persona MkmAgentLoops` → `docs/final/artifacts/mkm_agent_loops_v1_latest.md` |
| 【프리미엄 큐 권장】 | `… -Persona PremiumMultilensQueue` |
| 【Design 레인】 | `… -Persona DesignLane` |
| **딥리서치** · deep research · 논문 조사 | **Tier 0** Gemini→`docs/research/raw/` · **Tier 1** `mkm-deep-research/SKILL.md`(LIT_REVIEW md) · **0→1 merge** `*_MERGED_LIT_REVIEW_*.md` SSOT · **Tier 2** pytest exit 0 |
| **소화** · 논문 소화 · digest paper | `py scripts/run_mkm_paper_digest_v1.py --pdf <path> --lens logos\|myeongri\|ijeoma` 또는 `--lens logos` (HAAN 배치) → Tier0 + digestion chain · SSOT `mkm_paper_digest_run_v1_latest.json` · 규칙 `mkm-paper-digest-trigger-v1.mdc` |
| **논문 디스크 4칸** · paper verdict · tier 절단 · LIT_REVIEW 대조 | `@.cursor/rules/mkm-paper-disk-verdict-four-slot-v1.mdc` — Disk verdict · Reproduce · raw/repair_v2 · Promotion; support-fire only; `send_gate: HOLD` default |

→ 나머지 40+ 행: **`AGENTS_REFERENCE_V1.md` 「페르소나 단축 호출」**

## 핵심 SSOT 포인터
| 주제 | 경로 |
|------|------|
| 정체성·분기 | `docs/final/CENTRAL_AGENT_MEMORY_V1.md` |
| 작전 보드 | `MISSION_LOG.md` (로컬) |
| 로컬↔VPS | `docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md` |
| Fact-Lock 번들 | `scripts/run_fact_lock_bundle.ps1` |
| Trust Composition Design | `docs/final/MKM_TRUST_COMPOSITION_DESIGN_PIPELINE_V1.md` · `Run-ClinicLoiLandingDesignChain_v1.ps1` |
| Cursor 세션 baseline | `docs/final/CURSOR_SESSION_VALIDATION_BASELINE_V1.md` |
| **UMR G2 (U2 포인터)** | `@.cursor/rules/mkm_universal_os_g2.mdc` · G2 `g2a_*` 아티팩트 |
| Pillar A LTM · suspect_first | `reports/mkm_bench_2026_003_pillar_a_signoff_v1_latest.json` · `mkm_meta_coordinator_turn_contract_v1_latest.md` |
| **딥리서치 (논문·학술)** | Tier 0 `docs/research/raw/` · Tier 1 `mkm-deep-research/SKILL.md` · Tier 2 exit 0 · **DR bench 헬스/Fact-Lock:** `-IncludeDeepResearchBenchSmoke` / `-DeepResearchBenchSmokeOnly` (`run_workspace_automation_health.ps1`) · CONSTITUTION DR bench mini 표 |
| **Logos OSS (open-core harness)** | `py scripts/run_logos_oss_premarket_smoke_v1.py` · `py scripts/build_logos_oss_public_export_bundle_v1.py --materialize` → `exports/mkm-logos-research-oss-v1/` · manifest `logos_oss_public_export_manifest_v1.json` · **monorepo GitHub push ≠ export** |
| 인프라·GPU·PC 경로 | `docs/final/LOCAL_MACHINE_POINTER_V1.md` (비추적) |
| **Cursor hub · ops inbox** | `py scripts/run_mkm_ops_event_inbox_v1.py` (`enqueue`/`drain`/`status`) · JSONL `reports/mkm_ops_event_inbox_v1.jsonl` · SSOT `mkm_ops_event_inbox_v1_latest.*` · 초등 `reports/human_paste/mkm_ops_event_inbox_elementary_v1.txt` · ask/forbidden 자동 금지 |
| **Notion 발행 (API · MCP 아님)** | `NOTION_TOKEN`+`NOTION_PARENT_PAGE_ID` · bot `MKM Baekje A1` · `py scripts/publish_mkm_hallucination_control_notion_pack_v1.py` 또는 inbox `publish_notion_pack` → drain · **Notion MCP 추가 금지(lean)** · Publish to web OFF |

## Git · 원격 (한 줄)

- 기본 push: `scripts/push-internal.ps1` → **gitea/internal** only · GitHub `Push-GitHub-Explicit.ps1 -Acknowledge` 예외 · `1작업=1브랜치=1PR` · 솔로 `SoloDev-MergeFeatureToGiteaMain.ps1`.

## User Rules (Cursor Settings · 레포 밖)

- 권장: `docs/final/artifacts/cursor_user_rules_minimal_v1.txt` User 탭 복붙 · 장문 `AGENTS_REFERENCE_V1.md` 「Recommended Cursor User Rules」— **이중 주입 금지**

## MCP · 도구 카탈로그 (컨텍스트)

- lean 7 `.cursor/mcp.json` · NL `@notebooklm-mcp-session-bridge` · 웹 `@autonomous-web-search-v1` · `check_notebooklm_mcp_prereqs.ps1` · `Invoke-McpHygieneProbe.ps1` · openchrome/hostinger **요청 시만**
- **Notion:** MCP 미연결(의도) · 자동화는 **API** (`NOTION_TOKEN`) + ops inbox — 채팅에서 Notion을 자주 편집할 필요가 생기기 전 MCP 추가 금지

## `.cursorrules` (TITAN · Slim v2) · 확장

- SSOT 템플릿: `docs/final/artifacts/cursorrules_slim_ssot_v1.txt` — 루트와 **동기** (`enforce_cursorrules_slim_ssot.py` · `check_cursorrules_template_drift_v1.py` · diet `--strict`). 레인별 확장·압축·B-track·쇼룸 → **`AGENTS_REFERENCE_V1.md`**. `CLAUDE.md` = 개발 진입 요약.
