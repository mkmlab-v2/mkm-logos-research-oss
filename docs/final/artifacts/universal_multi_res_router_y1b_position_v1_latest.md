# Universal Multi-Res Router — Y1b 포지션 (Fact-Lock v1)

- **schema:** `universal_multi_res_router_y1b_position_v1`
- **version:** `1.0.0`
- **rail:** `B_TRACK` · **send_gate:** `HOLD` · **research_only:** `true`
- **SSOT:** `TRACK_C` §3.0b · §3.0d · §3.11 · `FAIL-COMP-004`

## 한 줄

MKM 대외 Y1 Hero는 **`mkm-universal-root` Dual-Plane 신뢰**이고, `universal_multi_res_router_v1`은 **Y1b monorepo B-track 실행 스캐폴드**(플러그인·게이트·감사 JSON)입니다. 「전처리 필터 독점」·「산업 표준 완성」 주장은 **금지**.

## Y1 Hero vs Y1b OS

| 축 | 역할 | 재현 |
|----|------|------|
| **Y1 Hero** | lexicon·topology dual-plane, fixture smoke, OSS GTM | `py scripts/run_universal_root_oss_cursor_smoke_v1.py` |
| **Y1b OS** | Neuro→Symbolic→Human 게이트, multi-res router, shallow adapter | `py scripts/universal_multi_res_router_v1.py --query "<intent>"` |
| **Parallel (압축)** | Plugin `zone_*.json` · IR 70/20/10 — **합산 금지** | `domain_router.py` 등 별 레인 |

## 시장 관측 [HYPO] (과장 금지)

- Commodity LLM 위에 **통제·감사·정책 일관** 레이어 수요 → 방어 가능한 서사.
- 벤더 내장 safety/memory API는 **대체 위협** (§3.11(3)).
- MKM moat 축: **export 가능한 게이트·checkpoint·감사 JSON** + dual-plane + domain killer UX (§3.11(7)).

## 라우터 Fact-Lock (디스크)

| 항목 | 팩트 |
|------|------|
| Router | `scripts/universal_multi_res_router_v1.py` v1.1.0 |
| Plugin registry | `scripts/build_universal_multi_res_plugin_registry_v1.py` |
| 1호 full | `sasang_context_v1` + 908-class inventory |
| 2호 lite_plus | `logos_lens_v1` + `logos_context_inventory_v1` |
| 명리 lite | `myeongni_lens_v1` + lite matrix + conflict runtime |
| 어댑터 | Ollama `mkm-shallow-router-v1` optional; keyword 폴백 허용 |
| 상용 | `metering_enabled: false` · `stub_status: pre_registration_only` |
| U2 훅 | 레인별 `.mdc` · **`alwaysApply: false`** (전역 mandatory 금지) |

## NEVER (대외·채팅)

- 「백퍼센트·예외 없이 수렴·이미 시장 표준」
- 「LLM 하위 노예」— 대외는 **검증 배관·게이트 레이어** (§3.1.8)
- 압축 KPI와 라우터·게이트 **동일 퍼널 합선** (FAIL-COMP-004)
- `send_gate` / Track A 승격 채팅 해제

## 재현

```powershell
py scripts/build_universal_multi_res_plugin_registry_v1.py
py scripts/universal_multi_res_router_v1.py --query "사상 stress 계산"
py -m pytest tests/test_universal_multi_res_router_v1.py tests/test_universal_multi_res_plugin_registry_v1.py tests/test_mkm_universal_multi_res_router_sasang_hook_v1.py -q
```
