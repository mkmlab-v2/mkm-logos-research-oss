# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.4, M:0.6}
# Balance: 91
# Purpose: Generate EN/KO external briefing markdown from Fact-Lock artifacts.
# Keywords: briefing, markdown, artifacts, governance, generator
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

BACKTEST_JSON = ART / "prophecy_lens_combo_backtest_v1_latest.json"
COORD_JSON = REPORTS / "mkm_global_coordinator_v1_latest.json"
VETO_JSON = ART / "sasang_veto_only_active_config_latest.json"
MAPPING_JSON = REPORTS / "lens_claims_evidence_mapping_v1_latest.json"
THIRTY_YEAR_JSON = ART / "prophecy_lens_combo_backtest_30y_latest.json"

OUT_EN = ART / "official_external_briefing_v1_latest.md"
OUT_KO = ART / "official_external_briefing_v1_latest.ko.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_num(value: Any, digits: int = 6) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"{num:.{digits}f}".rstrip("0").rstrip(".")


def _build_lines(
    backtest: dict[str, Any],
    coord: dict[str, Any],
    veto: dict[str, Any],
    thirty_year: dict[str, Any],
) -> dict[str, str]:
    generated_at = str(coord.get("generated_at_utc") or backtest.get("generated_at_utc") or "N/A")
    best = (backtest.get("best_strategy") or {})
    best_id = str(best.get("strategy_id") or "N/A")
    best_metrics = best.get("metrics") or {}
    best_cagr = _fmt_num(best_metrics.get("cagr"))
    best_sharpe = _fmt_num(best_metrics.get("sharpe"))
    best_mdd = _fmt_num(best_metrics.get("mdd"))

    logos_mdd = "N/A"
    for row in backtest.get("ranked_strategies") or []:
        if row.get("strategy_id") == "logos":
            logos_mdd = _fmt_num((row.get("metrics") or {}).get("mdd"))
            break

    global_policy = str((coord.get("coordinator") or {}).get("conflict_resolution_policy") or "N/A")
    conservative = (veto.get("hard_guardrails") or {}).get("most_conservative_wins")
    conservative_text = "true" if conservative is True else "false" if conservative is False else "N/A"
    coverage = thirty_year.get("coverage") or {}
    gate = thirty_year.get("thirty_year_claim_gate") or {}
    available_years = _fmt_num(coverage.get("available_years"), digits=4)
    thirty_status = str(gate.get("status") or "N/A")

    return {
        "generated_at": generated_at,
        "best_id": best_id,
        "best_cagr": best_cagr,
        "best_sharpe": best_sharpe,
        "best_mdd": best_mdd,
        "logos_mdd": logos_mdd,
        "global_policy": global_policy,
        "conservative": conservative_text,
        "available_years": available_years,
        "thirty_status": thirty_status,
    }


def _build_en(lines: dict[str, str]) -> str:
    return f"""# Official External Briefing v1 (Latest)

## Purpose
Externally safe summary grounded in current Fact-Lock artifacts, with explicit scope boundaries and governance guardrails.

## Status Badges
- `track`: `B_TRACK`
- `mode`: `research_only`
- `decision_role`: `non_gating`
- `promotion_gate`: `human_signoff_required`

## As-Of Anchor
- `as_of_utc`: `{lines["generated_at"]}`
- `artifact_scope`: `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json`
- `long_horizon_gate`: `docs/final/artifacts/prophecy_lens_combo_backtest_30y_latest.json` (`status={lines["thirty_status"]}`, `available_years={lines["available_years"]}`)
- `scope_note`: "Results are valid for the observed v1 horizon only; long-horizon generalization requires separate validation."

## External 5-Line Core Statement
1. **[Strategy Strength]** In the latest validated artifact scope, `{lines["best_id"]}` is ranked top (`best_strategy_id`) with `cagr={lines["best_cagr"]}`, `sharpe={lines["best_sharpe"]}`, and `mdd={lines["best_mdd"]}`.
2. **[Risk Governance]** The Logos lens is operated as a risk/context layer, not a standalone execution trigger; within the same artifact horizon, standalone Logos shows `mdd={lines["logos_mdd"]}`.
3. **[Decision Policy]** Operationally, primary lanes are prioritized in global coordination, while Sasang veto guardrails can activate conservative protections in designated conditions.
4. **[Validation Boundary]** These statements are tied to versioned artifacts and bounded evaluation windows (`30y_status={lines["thirty_status"]}`, `available_years={lines["available_years"]}`); promotion to production follows the formal Promotion Loop (`B -> Commander approval -> A`).
5. **[Operating Posture]** The system remains under conservative guardrails until unresolved items are cleared with evidence-backed updates.

## Policy Clarifier (Avoid Misinterpretation)
| Policy Surface | Active Rule | Source |
|---|---|---|
| Global coordinator conflict policy | `{lines["global_policy"]}` | `reports/mkm_global_coordinator_v1_latest.json` |
| Sasang veto hard guardrail | `most_conservative_wins={lines["conservative"]}` | `docs/final/artifacts/sasang_veto_only_active_config_latest.json` |

## Evidence Block (1:1 Mapping)
- Canonical claim mapping: `reports/lens_claims_evidence_mapping_v1_latest.json`
- Strategy ranking/mdd source: `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json`
- Long-horizon (30y) guard source: `docs/final/artifacts/prophecy_lens_combo_backtest_30y_latest.json`
- Sasang promotion gates: `reports/agct_sasang_stage2_promotion_gate_v1_latest.json`
- Sasang fasttrack gate: `reports/agct_sasang_stage2_fasttrack_gate_v1_latest.json`
- Sasang D+7 checkpoint: `reports/agct_sasang_stage2_d7_checkpoint_v1_latest.json`
- Track wall/autobind lock: `docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json`

## Required Footer for External Use
- No claim in this briefing should be interpreted as guaranteed future performance.
- Any production promotion requires explicit human sign-off and governance gate passage.
- If an expected artifact is missing, the corresponding claim is treated as `NOT_PROVEN`.
"""


def _build_ko(lines: dict[str, str]) -> str:
    return f"""# 공식 대외 브리핑 v1 (최신)

## 목적
현재 Fact-Lock 아티팩트에 근거하여, 범위 경계와 거버넌스 가드레일을 명시한 대외 안전 요약을 제공합니다.

## 상태 배지
- `track`: `B_TRACK`
- `mode`: `research_only`
- `decision_role`: `non_gating`
- `promotion_gate`: `human_signoff_required`

## 기준 시점(As-Of Anchor)
- `as_of_utc`: `{lines["generated_at"]}`
- `artifact_scope`: `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json`
- `long_horizon_gate`: `docs/final/artifacts/prophecy_lens_combo_backtest_30y_latest.json` (`status={lines["thirty_status"]}`, `available_years={lines["available_years"]}`)
- `scope_note`: "본 결과는 v1 관측 구간에 한정되며, 장기 구간 일반화는 별도 검증이 필요합니다."

## 대외 5문장 핵심 본문
1. **[전략 우위]** 최신 검증 아티팩트 범위에서 `{lines["best_id"]}` 조합은 `best_strategy_id` 1위를 기록했으며, `cagr={lines["best_cagr"]}`, `sharpe={lines["best_sharpe"]}`, `mdd={lines["best_mdd"]}`로 확인됩니다.
2. **[리스크 거버넌스]** Logos 렌즈는 단독 실행 트리거가 아닌 리스크/맥락 레이어로 운용되며, 동일 아티팩트 구간에서 단독 Logos의 `mdd={lines["logos_mdd"]}`이 관측됩니다.
3. **[의사결정 정책]** 운영상 전역 코디네이션은 주력 레인 우선 원칙을 따르며, 사상(Sasang) veto 가드레일은 지정 조건에서 보수적 보호를 활성화할 수 있습니다.
4. **[검증 경계]** 본 문장들은 버전 고정 아티팩트와 제한된 평가 윈도우(`30y_status={lines["thirty_status"]}`, `available_years={lines["available_years"]}`)에만 근거하며, 프로덕션 승격은 정식 Promotion Loop(`B -> Commander approval -> A`)를 따릅니다.
5. **[운영 기조]** 미해결 항목이 근거 기반으로 해소될 때까지 시스템은 보수적 가드레일 운영을 유지합니다.

## 정책 해설(오해 방지)
| 정책 표면 | 현재 규칙 | 근거 |
|---|---|---|
| 글로벌 코디네이터 충돌 정책 | `{lines["global_policy"]}` | `reports/mkm_global_coordinator_v1_latest.json` |
| 사상 veto 하드 가드레일 | `most_conservative_wins={lines["conservative"]}` | `docs/final/artifacts/sasang_veto_only_active_config_latest.json` |

## 근거 블록 (1:1 매핑)
- 표준 주장 매핑: `reports/lens_claims_evidence_mapping_v1_latest.json`
- 전략 순위/MDD 근거: `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json`
- 장기 구간(30y) 가드 근거: `docs/final/artifacts/prophecy_lens_combo_backtest_30y_latest.json`
- 사상 승격 게이트: `reports/agct_sasang_stage2_promotion_gate_v1_latest.json`
- 사상 패스트트랙 게이트: `reports/agct_sasang_stage2_fasttrack_gate_v1_latest.json`
- 사상 D+7 체크포인트: `reports/agct_sasang_stage2_d7_checkpoint_v1_latest.json`
- 트랙월/오토바인드 잠금: `docs/final/artifacts/sasang12_promotion_candidate_gate_latest.json`

## 대외 배포 필수 푸터
- 본 브리핑의 어떤 문장도 미래 성과를 보장하는 표현으로 해석되어서는 안 됩니다.
- 프로덕션 승격에는 명시적 human sign-off와 거버넌스 게이트 통과가 필수입니다.
- 기대 아티팩트가 누락된 경우 해당 주장은 `NOT_PROVEN`으로 처리합니다.
"""


def main() -> int:
    backtest = _load_json(BACKTEST_JSON)
    coord = _load_json(COORD_JSON)
    veto = _load_json(VETO_JSON)
    _ = _load_json(MAPPING_JSON)
    thirty_year = _load_json(THIRTY_YEAR_JSON) if THIRTY_YEAR_JSON.is_file() else {}

    lines = _build_lines(backtest, coord, veto, thirty_year)
    OUT_EN.write_text(_build_en(lines).strip() + "\n", encoding="utf-8")
    OUT_KO.write_text(_build_ko(lines).strip() + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_EN}")
    print(f"WROTE: {OUT_KO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
