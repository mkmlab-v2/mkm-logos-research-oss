---
name: mkm-sasang-lane-ops
description: 사상 레인 work-start — UMR sasang hook, read_order, interpretive bundle HOLD, daily unified adapter. Use when user mentions 사상·sasang·사상동역학·체질·병증·표리병증·pyobyeong, or @mkm-universal-multi-res-router-sasang-v1, or 【사상 작업 시작】.
---

# MKM 사상 레인 — Cursor work-start (opt-in)

**NOT:** 전역 두뇌 · Track A 승격 · `alwaysApply` 헌법 박제 · Logos/41k lexicon 합선.

**Rules:** `@mkm-universal-multi-res-router-sasang-v1` · `@mkm-sasang-pyobyeong-btrack-v1` (표리병증 시)

**SSOT:** `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (사상·pyobyeong·unified adapter·Advisory 행)

## 5-step checklist (매 사상 작업 시작)

1. **라우터** — 구현·범위·완료 주장 전:
   ```powershell
   py scripts/universal_multi_res_router_v1.py --query "<의도 한 줄>"
   ```
   Read `docs/final/artifacts/universal_multi_res_router_v1_latest.json` — `hold_gate` / `forbidden_hits` 있으면 **중단**.

2. **read_order** — `high_res` 시 `domain_plugin.agent_read_order` 핵심만 (전부 생략 금지):
   - `sasang_dynamics_btrack_milestone_v1_latest.json` (`closed_btrack_middleware_v1`)
   - `sasang_interpretive_insight_bundle_v1_latest.json`
   - `SASANG_DYNAMICS_V1_CONTRACT.json`

3. **번들 게이트** — `send_gate: HOLD` · `decision_authority: human_only` · `synthesis_v1.forbidden_synthesis_ko` 인용 (합성 금지).

4. **일일 동역학** — 본선 stress/stage는 디스크만:
   ```powershell
   py scripts/run_sasang_dynamics_unified_adapter_v1.py --profile mainline
   ```
   Read `reports/sasang_dynamics_unified_v1_latest.json` (없으면 `run_sasang_unified_adapter_daily_chain_v1.py`).

5. **통과 주장** — 채팅 기억 금지; 아래 중 해당 smoke **exit 0**:
   ```powershell
   powershell -File scripts\run_workspace_automation_health.ps1 -SasangPyobyeongBtrackSmokeOnly
   ```
   또는 `… -Persona SasangRailStack` (주간 풀스택).

## Advisory / daily brief (통찰 연결됨)

- Parallel Advisory 사상 슬라이스: `interpretive_bundle_enrichment` in `reports/mkm_parallel_advisory_brief_v1_latest.json`
- Daily brief: `py scripts/build_daily_execution_insight_brief_v1.py`

## NEVER

- gematria/Track A 커널 합선 · 임상·CDSS 자동승격 · `promotion_to_a_track_allowed` 해제 주장
- 31k Logos 코퍼스와 41,658 lexicon **단일 코퍼스** 혼동 (`mkm_anchor_map_operator_v1_latest.json`)

## Reproduce (한 번에)

```powershell
cd C:\workspace
py scripts/universal_multi_res_router_v1.py --query "사상 stress interpretive bundle"
py scripts/run_sasang_unified_adapter_daily_chain_v1.py --skip-lens-refresh
py -m pytest tests/test_sasang_unified_adapter_daily_chain_v1.py tests/test_sasang_interpretive_insight_bundle_v1.py -q
```
