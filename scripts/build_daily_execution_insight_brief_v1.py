#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Materialize `DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md` fields from disk SSOT JSON only.

Outputs a 1-page Markdown brief (observation / hygiene — not trading advice).
Template SSOT: projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FUSION = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_stub_latest.json"
DEFAULT_THIN = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "multilens_eval_v2_thin_report_latest.json"
DEFAULT_OUT = WORKSPACE_ROOT / "reports" / "daily_execution_insight_brief_latest.md"
_ART = WORKSPACE_ROOT / "docs" / "final" / "artifacts"
DEFAULT_MYEONGNI_LENS = _ART / "myeongni_independent_lens_latest.json"
DEFAULT_SASANG_LENS = _ART / "sasang_independent_lens_latest.json"
DEFAULT_SASANG_INTERPRETIVE_BUNDLE = _ART / "sasang_interpretive_insight_bundle_v1_latest.json"
DEFAULT_MARKET_SASANG_LENS = _ART / "market_sasang_lens_latest.json"
DEFAULT_MARKET_MYEONGNI_LENS = _ART / "market_myeongni_lens_latest.json"
DEFAULT_LOGOS_INDEPENDENT_LENS = _ART / "logos_independent_lens_latest.json"
DEFAULT_A_TRACK_GONOGO = _ART / "a_track_go_nogo_status_latest.json"
DEFAULT_PROPHECY_MONTHLY = _ART / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
DEFAULT_LENS_BACKTEST = _ART / "prophecy_lens_combo_backtest_v1_latest.json"
DEFAULT_MYEONGNI_16STATE = WORKSPACE_ROOT / "data" / "myeongni" / "16_STATE_MASTER_PROBE_v1.json"
DEFAULT_COMMANDER_MYEONGNI = WORKSPACE_ROOT / "reports" / "commander_myeongni_lens_latest.json"
DEFAULT_SASANG_VETO_CFG = _ART / "sasang_veto_only_active_config_latest.json"
DEFAULT_MYEONGRI_V2_UPGRADE = WORKSPACE_ROOT / "reports" / "myeongri_core_v2_upgrade_latest.json"
DEFAULT_MYEONGNI_CONFLICT_RUNTIME = (
    WORKSPACE_ROOT / "reports" / "myeongni_conflict_arbitration_runtime_mode_latest.json"
)


def _abs_under_root(root: Path, p: Path) -> Path:
    return p.resolve() if p.is_absolute() else (root / p).resolve()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _utc_date_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _pick_thin_row(
    report: dict[str, Any], calendar_date: str | None
) -> tuple[dict[str, Any] | None, str | None]:
    rows = report.get("rows")
    if not isinstance(rows, list):
        return None, None
    if calendar_date:
        for r in rows:
            if isinstance(r, dict) and r.get("calendar_date") == calendar_date:
                return r, calendar_date
    for r in reversed(rows):
        if not isinstance(r, dict):
            continue
        lo = r.get("lens_outputs")
        if not isinstance(lo, dict):
            continue
        ldr = lo.get("logos_dual_regime")
        if ldr:
            return r, str(r.get("calendar_date") or "")
    return None, None


def _md_cell(val: Any) -> str:
    s = "" if val is None else str(val)
    return s.replace("|", "\\|").replace("\n", " ").strip()


def _num_opt(x: Any, nd: int = 4) -> str:
    if isinstance(x, bool):
        return str(x)
    try:
        if x is None:
            return "—"
        f = float(x)
        if f != f:
            return "—"
        return f"{f:.{nd}g}"
    except (TypeError, ValueError):
        return _md_cell(x)


def _fmt_row_note(thin_path: Path, picked_date: str | None, ok: bool) -> str:
    if ok:
        return f"`{thin_path.as_posix()}` row `calendar_date={picked_date}`"
    return f"`{thin_path.as_posix()}` — no populated `logos_dual_regime` row (run thin harness with `--populate-default-samples`)"


def _lines_myeongni(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Myeongni (`myeongni_independent_lens_latest`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    mso = doc.get("myeongri_stream_outputs")
    mso = mso if isinstance(mso, dict) else {}
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `ts_utc` | {_md_cell(doc.get('ts_utc'))} |")
    lines.append(f"| `schema` | {_md_cell(doc.get('schema'))} |")
    lines.append(f"| `direction_score` | {_num_opt(scores.get('direction_score'))} |")
    lines.append(f"| `confidence` | {_num_opt(scores.get('confidence'))} |")
    lines.append(f"| `state_id` | {_md_cell(mso.get('state_id'))} |")
    lines.append(f"| `run_id` | {_md_cell(mso.get('run_id'))} |")
    lines.append("")
    return lines, True


def _lines_sasang(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Sasang (`sasang_independent_lens_latest`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    sso = doc.get("sasang_stream_outputs")
    sso = sso if isinstance(sso, dict) else {}
    mr = sso.get("machine_readables")
    mr = mr if isinstance(mr, dict) else {}
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `ts_utc` | {_md_cell(doc.get('ts_utc'))} |")
    lines.append(f"| `mapping_target` | {_md_cell(sso.get('mapping_target'))} |")
    lines.append(f"| `regime_hypothesis` | {_md_cell(sso.get('regime_hypothesis'))} |")
    lines.append(f"| `direction_score` | {_num_opt(scores.get('direction_score'))} |")
    lines.append(f"| `confidence` | {_num_opt(scores.get('confidence'))} |")
    lines.append(f"| `heat_proxy` | {_num_opt(mr.get('heat_proxy'))} |")
    lines.append(f"| `cold_proxy` | {_num_opt(mr.get('cold_proxy'))} |")
    lines.append(f"| `volatility_rarefaction_proxy` | {_num_opt(mr.get('volatility_rarefaction_proxy'))} |")
    lines.append("")
    ax = doc.get("b_track_axis_scores_v1")
    if isinstance(ax, dict) and str(ax.get("schema")) == "sasang_b_track_axis_scores_v1":
        lines.append("##### `b_track_axis_scores_v1` (동역학 프록시만; 보명·금화 본론 정량 아님)")
        lines.append("")
        lines.append("| field | value |")
        lines.append("|-------|-------|")
        lines.append(f"| `heat_proxy` | {_num_opt(ax.get('heat_proxy'))} |")
        lines.append(f"| `cold_proxy` | {_num_opt(ax.get('cold_proxy'))} |")
        lines.append(f"| `volatility_rarefaction_proxy` | {_num_opt(ax.get('volatility_rarefaction_proxy'))} |")
        lines.append(f"| `thermal_imbalance_proxy` | {_num_opt(ax.get('thermal_imbalance_proxy'))} |")
        dk = ax.get("disclaimer_ko")
        if dk:
            lines.append("")
            lines.append(f"> {_md_cell(dk)}")
    else:
        lines.append("##### `b_track_axis_scores_v1`")
        lines.append("")
        lines.append(
            f"*(block missing — regenerate with `scripts/run_lens_sasang.py`; lens file `{path.as_posix()}`)*"
        )
    lines.append("")
    return lines, True


def _lines_sasang_interpretive_bundle(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Sasang interpretive bundle (`sasang_interpretive_insight_bundle_v1`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    syn = doc.get("synthesis_v1") if isinstance(doc.get("synthesis_v1"), dict) else {}
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `version` | {_md_cell(doc.get('version'))} |")
    lines.append(f"| `rail` | {_md_cell(doc.get('rail'))} |")
    lines.append(f"| `decision_authority` | {_md_cell(doc.get('decision_authority'))} |")
    lines.append(f"| `send_gate` | `{_md_cell(doc.get('send_gate') or 'HOLD')}` |")
    forbidden = syn.get("forbidden_synthesis_ko")
    if forbidden:
        excerpt = str(forbidden)
        if len(excerpt) > 220:
            excerpt = excerpt[:217] + "..."
        lines.append(f"| `forbidden_synthesis_ko` (excerpt) | {_md_cell(excerpt)} |")
    lines.append("")
    lines.append(
        "> `[NON_GATING]` 축·금지합성 참조 — direction merge·Track A·실매매 트리거 금지."
    )
    lines.append("")
    return lines, True


def _lines_market_myeongni(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    """Finance overlay on universal myeongni JSON (Track B) — not a second calendar engine."""
    lines: list[str] = []
    lines.append("#### Market Myeongni (`market_myeongni_lens_latest`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    if str(doc.get("schema")) != "market_myeongni_lens_v1":
        lines.append(
            f"*(schema not `market_myeongni_lens_v1` — got `{_md_cell(doc.get('schema'))}`; `{path.as_posix()}`)*"
        )
        lines.append("")
        return lines, False
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    ov = doc.get("overlay") if isinstance(doc.get("overlay"), dict) else {}
    ap = ov.get("applied") if isinstance(ov.get("applied"), dict) else {}
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `ts_utc` | {_md_cell(doc.get('ts_utc'))} |")
    lines.append(f"| `direction_score` (overlay) | {_num_opt(scores.get('direction_score'))} |")
    lines.append(f"| `confidence` (overlay) | {_num_opt(scores.get('confidence'))} |")
    lines.append(f"| `direction_sign` | {_md_cell(doc.get('direction_sign'))} |")
    lines.append(f"| `base_direction_score` | {_num_opt(ov.get('base_direction_score'))} |")
    lines.append(f"| `base_confidence` | {_num_opt(ov.get('base_confidence'))} |")
    lines.append(f"| `direction_score_scale` | {_num_opt(ap.get('direction_score_scale'))} |")
    lines.append(f"| `confidence_scale` | {_num_opt(ap.get('confidence_scale'))} |")
    pol = str(ov.get("policy_path") or "")
    if pol:
        lines.append(f"| `policy_path` | `{pol}` |")
    lines.append("")
    return lines, True


def _policy_hash_short(h: Any, n: int = 12) -> str:
    s = "" if h is None else str(h).strip()
    if len(s) <= n:
        return s
    return s[:n] + "…"


def _lines_myeongni_conflict_runtime(
    doc: dict[str, Any] | None, path: Path
) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Myeongni conflict arbitration runtime (B-track policy stamp)")
    lines.append("")
    lines.append(
        "> Policy mode / verification only — not a price signal and not wired to live execution."
    )
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    if str(doc.get("schema")) != "myeongni_conflict_arbitration_runtime_mode_v1":
        lines.append(
            f"*(schema not `myeongni_conflict_arbitration_runtime_mode_v1` — "
            f"got `{_md_cell(doc.get('schema'))}`)*"
        )
        lines.append("")
        return lines, False
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `mode` | {_md_cell(doc.get('mode'))} |")
    lines.append(f"| `verification_pass` | {_md_cell(doc.get('verification_pass'))} |")
    lines.append(f"| `policy_hash` | `{_policy_hash_short(doc.get('policy_hash'))}` |")
    lines.append(f"| `generated_at_utc` | {_md_cell(doc.get('generated_at_utc'))} |")
    pp = str(doc.get("policy_path") or "")
    if pp:
        lines.append(f"| `policy_path` | `{pp}` |")
    lines.append("")
    return lines, True


def _lines_market_sasang(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Market Sasang (`market_sasang_lens_latest`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    hcg = doc.get("human_commander_gate_v1")
    hcg = hcg if isinstance(hcg, dict) else {}
    sv = doc.get("state_vector_sasang_softmax")
    sv = sv if isinstance(sv, dict) else {}
    unc = doc.get("uncertainty")
    unc = unc if isinstance(unc, dict) else {}
    veto = doc.get("veto")
    veto = veto if isinstance(veto, dict) else {}
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `ts_utc` | {_md_cell(doc.get('ts_utc'))} |")
    lines.append("")
    lines.append(f"- **human_commander banner:** {_md_cell(hcg.get('banner_ko'))}")
    lines.append(
        f"- **`veto.force_hold`:** `{_md_cell(veto.get('force_hold'))}` · "
        f"`reason_codes` = `{json.dumps(veto.get('reason_codes'), ensure_ascii=False)}`"
    )
    lines.append(
        f"- **`composite_uncertainty`:** {_num_opt(unc.get('composite_uncertainty'))} · "
        f"`entropy_norm_4way` = {_num_opt(unc.get('entropy_norm_4way'))}"
    )
    lines.append("")
    lines.append("| softmax key | p |")
    lines.append("|-------------|---|")
    for k in ("taeyang", "soyang", "taeeum", "soeum"):
        lines.append(f"| `{k}` | {_num_opt(sv.get(k))} |")
    lines.append("")
    return lines, True


def _lines_logos_independent(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Logos independent lens (`logos_independent_lens_latest`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    ev = doc.get("evidence_refs")
    n_ev = len(ev) if isinstance(ev, list) else 0
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `ts_utc` | {_md_cell(doc.get('ts_utc'))} |")
    lines.append(f"| `direction_score` | {_num_opt(scores.get('direction_score'))} |")
    lines.append(f"| `confidence` | {_num_opt(scores.get('confidence'))} |")
    lines.append(f"| `evidence_refs_count` | {n_ev} |")
    lines.append("")
    narr = str(doc.get("narrative_snippet_guarded") or "").strip()
    lines.append("**`narrative_snippet_guarded` (hash-tagged only):**")
    lines.append("")
    lines.append("```")
    lines.append(narr or "*(empty)*")
    lines.append("```")
    lines.append("")
    return lines, True


def _lines_factlock_governance(
    *,
    a_track: dict[str, Any] | None,
    a_track_path: Path,
    prophecy_monthly: dict[str, Any] | None,
    prophecy_monthly_path: Path,
    lens_backtest: dict[str, Any] | None,
    lens_backtest_path: Path,
    myeongni_16state: dict[str, Any] | None,
    myeongni_16state_path: Path,
    commander_myeongni: dict[str, Any] | None,
    commander_myeongni_path: Path,
    sasang_veto_cfg: dict[str, Any] | None,
    sasang_veto_cfg_path: Path,
) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("### 1d) Fact-Lock governance snapshot (A-track / backtest / commander overlay)")
    lines.append("")
    lines.append("| field | value | source |")
    lines.append("|-------|-------|--------|")

    ok = False
    if a_track:
        result = a_track.get("result") if isinstance(a_track.get("result"), dict) else {}
        snap = a_track.get("snapshot") if isinstance(a_track.get("snapshot"), dict) else {}
        checks = a_track.get("checks") if isinstance(a_track.get("checks"), dict) else {}
        lines.append(
            f"| `overall_go_no_go` | `{_md_cell(result.get('overall_go_no_go'))}` | `{a_track_path.as_posix()}` |"
        )
        lines.append(
            f"| `recommended_stage` | `{_md_cell(result.get('recommended_stage'))}` | `{a_track_path.as_posix()}` |"
        )
        lines.append(
            f"| `failed_reasons` | `{_md_cell(json.dumps(result.get('failed_reasons'), ensure_ascii=False))}` | `{a_track_path.as_posix()}` |"
        )
        lines.append(
            f"| `high_reliability_decision` | `{_md_cell(snap.get('high_reliability_decision'))}` | `{a_track_path.as_posix()}` |"
        )
        lines.append(
            f"| `price_output_locked` | `{_md_cell(snap.get('price_output_locked'))}` | `{a_track_path.as_posix()}` |"
        )
        lines.append(
            f"| `price_output_unlocked(check)` | `{_md_cell(checks.get('price_output_unlocked'))}` | `{a_track_path.as_posix()}` |"
        )
        ok = True
    else:
        lines.append(f"| `a_track_go_nogo_status` | `missing` | `{a_track_path.as_posix()}` |")

    if prophecy_monthly:
        meta = prophecy_monthly.get("meta") if isinstance(prophecy_monthly.get("meta"), dict) else {}
        lines.append(
            f"| `prophecy.meta.high_reliability_decision` | `{_md_cell(meta.get('high_reliability_decision'))}` | `{prophecy_monthly_path.as_posix()}` |"
        )
        lines.append(
            f"| `prophecy.meta.price_output_locked` | `{_md_cell(meta.get('price_output_locked'))}` | `{prophecy_monthly_path.as_posix()}` |"
        )
        ok = True
    else:
        lines.append(f"| `prophecy_monthly` | `missing` | `{prophecy_monthly_path.as_posix()}` |")

    if lens_backtest:
        best = lens_backtest.get("best_strategy") if isinstance(lens_backtest.get("best_strategy"), dict) else {}
        metrics = best.get("metrics") if isinstance(best.get("metrics"), dict) else {}
        lines.append(
            f"| `best_strategy.strategy_id` | `{_md_cell(best.get('strategy_id'))}` | `{lens_backtest_path.as_posix()}` |"
        )
        lines.append(
            f"| `best_strategy.metrics.n_days` | `{_md_cell(metrics.get('n_days'))}` | `{lens_backtest_path.as_posix()}` |"
        )
        lines.append(
            f"| `best_strategy.metrics.mdd` | `{_num_opt(metrics.get('mdd'))}` | `{lens_backtest_path.as_posix()}` |"
        )
        lines.append(
            f"| `best_strategy.metrics.sharpe` | `{_num_opt(metrics.get('sharpe'))}` | `{lens_backtest_path.as_posix()}` |"
        )
        ok = True
    else:
        lines.append(f"| `lens_combo_backtest` | `missing` | `{lens_backtest_path.as_posix()}` |")

    if myeongni_16state:
        cov = myeongni_16state.get("coverage_summary") if isinstance(myeongni_16state.get("coverage_summary"), dict) else {}
        lines.append(
            f"| `16state.states_with_audit` | `{_md_cell(cov.get('states_with_audit'))}` | `{myeongni_16state_path.as_posix()}` |"
        )
        lines.append(
            f"| `16state.states_total` | `{_md_cell(cov.get('states_total'))}` | `{myeongni_16state_path.as_posix()}` |"
        )
        ok = True
    else:
        lines.append(f"| `16_state_master_probe` | `missing` | `{myeongni_16state_path.as_posix()}` |")

    if commander_myeongni:
        scores = commander_myeongni.get("scores") if isinstance(commander_myeongni.get("scores"), dict) else {}
        lines.append(
            f"| `commander.scores.confidence` | `{_num_opt(scores.get('confidence'))}` | `{commander_myeongni_path.as_posix()}` |"
        )
        lines.append(
            f"| `commander.scores.direction_score` | `{_num_opt(scores.get('direction_score'))}` | `{commander_myeongni_path.as_posix()}` |"
        )
        ok = True
    else:
        lines.append(f"| `commander_myeongni_lens` | `missing` | `{commander_myeongni_path.as_posix()}` |")

    if sasang_veto_cfg:
        hg = sasang_veto_cfg.get("hard_guardrails") if isinstance(sasang_veto_cfg.get("hard_guardrails"), dict) else {}
        lines.append(
            f"| `sasang.hard_guardrails.most_conservative_wins` | `{_md_cell(hg.get('most_conservative_wins'))}` | `{sasang_veto_cfg_path.as_posix()}` |"
        )
        lines.append(
            f"| `sasang.hard_guardrails.directional_entry_disabled` | `{_md_cell(hg.get('directional_entry_disabled'))}` | `{sasang_veto_cfg_path.as_posix()}` |"
        )
        ok = True
    else:
        lines.append(f"| `sasang_veto_cfg` | `missing` | `{sasang_veto_cfg_path.as_posix()}` |")

    lines.append("")
    lines.append(
        "- **Label discipline:** `GO`/`HOLD`는 운영 게이트(`overall_go_no_go`) 기준, "
        "`PASS`/`FAIL`은 개별 체크(`high_reliability_decision` 등) 기준으로 분리 기록."
    )
    lines.append("")
    return lines, ok


def _lines_myeongri_v2_upgrade(
    doc: dict[str, Any] | None, path: Path
) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("### 1e) Myeongri core v2 upgrade (jijangan vector / research shinsal / size reco)")
    lines.append("")
    lines.append("| field | value | source |")
    lines.append("|-------|-------|--------|")
    if not doc or str(doc.get("schema") or "") != "myeongri_core_v2_upgrade_v1":
        lines.append(f"| `myeongri_core_v2_upgrade` | `missing or invalid schema` | `{path.as_posix()}` |")
        lines.append("")
        lines.append(
            "- **Refresh:** `py scripts/myeongri_core_v2_upgrade.py` (reads `commander_myeongni_lens_latest.json` by default)."
        )
        lines.append("")
        return lines, False

    out = doc.get("output") if isinstance(doc.get("output"), dict) else {}
    jw = doc.get("jijangan_weighted_vector") if isinstance(doc.get("jijangan_weighted_vector"), dict) else {}
    elems = jw.get("elements") if isinstance(jw.get("elements"), dict) else {}
    sh = doc.get("shinsal_impact_overlay") if isinstance(doc.get("shinsal_impact_overlay"), dict) else {}
    detected = sh.get("detected") if isinstance(sh.get("detected"), list) else []

    lines.append(
        f"| `output.size_multiplier_recommended` | `{_num_opt(out.get('size_multiplier_recommended'))}` | `{path.as_posix()}` |"
    )
    lines.append(
        f"| `output.commander_overlay_multiplier` | `{_num_opt(out.get('commander_overlay_multiplier'))}` | `{path.as_posix()}` |"
    )
    lines.append(
        f"| `output.direction_override_allowed` | `{_md_cell(out.get('direction_override_allowed'))}` | `{path.as_posix()}` |"
    )
    nsm = doc.get("neutral_structure_metrics_v1")
    if isinstance(nsm, dict):
        lines.append(
            f"| `neutral.structural_tension_v1` | `{_num_opt(nsm.get('structural_tension_v1'))}` | `{path.as_posix()}` |"
        )
        lev = nsm.get("latent_energy_vector_4d")
        if isinstance(lev, list):
            lines.append(
                f"| `neutral.latent_energy_vector_4d` | `{_md_cell(json.dumps(lev, ensure_ascii=False))}` | `{path.as_posix()}` |"
            )
    sdl = doc.get("shinsal_detection_logs")
    if isinstance(sdl, dict):
        ent = sdl.get("entries") if isinstance(sdl.get("entries"), list) else []
        lines.append(f"| `shinsal_detection_logs.entries` | `{len(ent)}` | `{path.as_posix()}` |")
    notice = doc.get("b_track_notice")
    lines.append("")
    lines.append(f"> { _md_cell(notice) if notice else '[MKM-B-TRACK-NOTICE] (missing in JSON — regenerate v2)' }")
    lines.append("")
    for k in ("wood", "fire", "earth", "metal", "water"):
        lines.append(
            f"| `jijangan.elements.{k}` | `{_num_opt(elems.get(k))}` | `{path.as_posix()}` |"
        )
    lines.append(
        f"| `shinsal.detected_count` | `{len(detected)}` | `{path.as_posix()}` |"
    )
    if detected:
        ids = [str(x.get("id", "")) for x in detected if isinstance(x, dict)]
        lines.append(
            f"| `shinsal.detected_ids` | `{_md_cell(', '.join(ids))}` | `{path.as_posix()}` |"
        )
    lines.append("")
    lines.append(
        "- **Labels:** `[RESEARCH_ONLY]` on `shinsal_impact_overlay`; `neutral_structure_metrics_v1` is "
        "[HYPOTHESIS] geometry only (not price/vol); size output is advisory overlay only (no A-track direction)."
    )
    lines.append("")
    return lines, True


def build_markdown(
    *,
    brief_date_utc: str,
    workspace_anchor: str,
    fusion: dict[str, Any] | None,
    thin: dict[str, Any] | None,
    thin_path: Path,
    fusion_path: Path,
    calendar_date: str | None,
    myeongni: dict[str, Any] | None = None,
    myeongni_path: Path | None = None,
    sasang: dict[str, Any] | None = None,
    sasang_path: Path | None = None,
    sasang_interpretive_bundle: dict[str, Any] | None = None,
    sasang_interpretive_bundle_path: Path | None = None,
    market_sasang: dict[str, Any] | None = None,
    market_sasang_path: Path | None = None,
    market_myeongni: dict[str, Any] | None = None,
    market_myeongni_path: Path | None = None,
    logos_independent: dict[str, Any] | None = None,
    logos_independent_path: Path | None = None,
    a_track_gonogo: dict[str, Any] | None = None,
    a_track_gonogo_path: Path | None = None,
    prophecy_monthly: dict[str, Any] | None = None,
    prophecy_monthly_path: Path | None = None,
    lens_backtest: dict[str, Any] | None = None,
    lens_backtest_path: Path | None = None,
    myeongni_16state: dict[str, Any] | None = None,
    myeongni_16state_path: Path | None = None,
    commander_myeongni: dict[str, Any] | None = None,
    commander_myeongni_path: Path | None = None,
    sasang_veto_cfg: dict[str, Any] | None = None,
    sasang_veto_cfg_path: Path | None = None,
    myeongri_v2_upgrade: dict[str, Any] | None = None,
    myeongri_v2_upgrade_path: Path | None = None,
    myeongni_conflict_runtime: dict[str, Any] | None = None,
    myeongni_conflict_runtime_path: Path | None = None,
) -> str:
    lines: list[str] = []
    lines.append("# Daily execution insight — 1-page brief (generated)")
    lines.append("")
    lines.append("**AUTO:** `scripts/build_daily_execution_insight_brief_v1.py` — Fact-Lock sources only; not LLM prose.")
    lines.append("")
    lines.append("## 0) Meta")
    lines.append("")
    lines.append(f"| `brief_date_utc` | {brief_date_utc} |")
    lines.append(f"| `workspace_anchor` | {workspace_anchor} |")
    lines.append("| `mode` | `OBSERVATION_ONLY` |")
    lines.append("")
    lines.append("## 1) Execution facts (disk)")
    lines.append("")
    lines.append("### 1a) Dual regime (snippet only — no full `interpretation` in brief)")
    lines.append("")
    snippet = ""
    cap_s = "—"
    shock_s = "—"
    veto_s = "—"
    thin_ok = False
    picked_date: str | None = None
    row_note = _fmt_row_note(thin_path, None, False)

    if thin:
        row, picked_date = _pick_thin_row(thin, calendar_date)
        if row:
            lo = row.get("lens_outputs")
            if isinstance(lo, dict):
                ldr = lo.get("logos_dual_regime")
                if isinstance(ldr, dict):
                    thin_ok = True
                    snippet = str(ldr.get("interpretation_snippet") or "").strip()
                    cap = ldr.get("risk_multiplier_cap")
                    cap_s = str(cap) if cap is not None else "—"
                    shock_s = str(ldr.get("market_shock_confirmed"))
                    veto_s = str(ldr.get("veto_triggered"))
                    row_note = _fmt_row_note(thin_path, picked_date or calendar_date, True)

    if not snippet:
        snippet = (
            "*(missing — ensure thin report is written to "
            f"`{thin_path.as_posix()}` with populated `interpretation_snippet`)*"
        )

    lines.append(f"- **Thin row:** {row_note}")
    lines.append("")
    lines.append("**`interpretation_snippet`:**")
    lines.append("")
    lines.append("```")
    lines.append(snippet)
    lines.append("```")
    lines.append("")
    lines.append(
        f"**Snapshot (one line):** `risk_multiplier_cap` = {cap_s} · "
        f"`market_shock_confirmed` = {shock_s} · `veto_triggered` = {veto_s}"
    )
    lines.append("")
    lines.append("### 1b) Independent lens fusion stub (`conflict_summary`)")
    lines.append("")
    lines.append(f"- **Source:** `{fusion_path.as_posix()}`")
    lines.append("")
    narrative = ""
    minority: list[str] = []
    verses: list[str] = []
    if fusion:
        cs = fusion.get("conflict_summary")
        if isinstance(cs, dict):
            narrative = str(cs.get("conflict_narrative_guarded") or "").strip()
            mi = cs.get("minority_lens_ids")
            if isinstance(mi, list):
                minority = [str(x) for x in mi]
            lv = cs.get("logos_evidence_verse_ids")
            if isinstance(lv, list):
                verses = [str(x) for x in lv]
        try:
            from scripts.report_independent_lens_fusion_stub_v0 import resolve_fusion_headline_v1

            hl = resolve_fusion_headline_v1(fusion)
            lines.append(
                f"- **`headline_gating`:** raw=`{hl.get('raw_consensus_sign')}` · "
                f"headline=`{hl.get('headline_sign')}` · demote=`{hl.get('demote_active')}` · "
                f"non_gating=`{hl.get('non_gating')}`"
            )
            lines.append("")
        except ImportError:
            pass

    lines.append(f"- **`minority_lens_ids`:** `{json.dumps(minority, ensure_ascii=False)}`")
    lines.append(f"- **`logos_evidence_verse_ids`:** `{json.dumps(verses, ensure_ascii=False)}`")
    lines.append("")
    lines.append("**`conflict_narrative_guarded`:**")
    lines.append("")
    lines.append("```")
    lines.append(narrative or "*(missing fusion artifact)*")
    lines.append("```")
    lines.append("")
    lines.append("### 1c) Independent lens snapshots (latest JSON — numeric / structured facts only)")
    lines.append("")
    mp = myeongni_path or DEFAULT_MYEONGNI_LENS
    sp = sasang_path or DEFAULT_SASANG_LENS
    mmp = market_myeongni_path or DEFAULT_MARKET_MYEONGNI_LENS
    msp = market_sasang_path or DEFAULT_MARKET_SASANG_LENS
    lp = logos_independent_path or DEFAULT_LOGOS_INDEPENDENT_LENS
    lm, ok_m = _lines_myeongni(myeongni, mp)
    lmm, ok_mm = _lines_market_myeongni(market_myeongni, mmp)
    crp = myeongni_conflict_runtime_path or DEFAULT_MYEONGNI_CONFLICT_RUNTIME
    lcr, ok_cr = _lines_myeongni_conflict_runtime(myeongni_conflict_runtime, crp)
    ls, ok_s = _lines_sasang(sasang, sp)
    sip = sasang_interpretive_bundle_path or DEFAULT_SASANG_INTERPRETIVE_BUNDLE
    lsib, ok_sib = _lines_sasang_interpretive_bundle(sasang_interpretive_bundle, sip)
    lms, ok_ms = _lines_market_sasang(market_sasang, msp)
    ll, ok_l = _lines_logos_independent(logos_independent, lp)
    lines.extend(lm)
    lines.extend(lmm)
    lines.extend(lcr)
    lines.extend(ls)
    lines.extend(lsib)
    lines.extend(lms)
    lines.extend(ll)
    atp = a_track_gonogo_path or DEFAULT_A_TRACK_GONOGO
    pmp = prophecy_monthly_path or DEFAULT_PROPHECY_MONTHLY
    lbp = lens_backtest_path or DEFAULT_LENS_BACKTEST
    m16p = myeongni_16state_path or DEFAULT_MYEONGNI_16STATE
    cmp = commander_myeongni_path or DEFAULT_COMMANDER_MYEONGNI
    svp = sasang_veto_cfg_path or DEFAULT_SASANG_VETO_CFG
    lg, ok_g = _lines_factlock_governance(
        a_track=a_track_gonogo,
        a_track_path=atp,
        prophecy_monthly=prophecy_monthly,
        prophecy_monthly_path=pmp,
        lens_backtest=lens_backtest,
        lens_backtest_path=lbp,
        myeongni_16state=myeongni_16state,
        myeongni_16state_path=m16p,
        commander_myeongni=commander_myeongni,
        commander_myeongni_path=cmp,
        sasang_veto_cfg=sasang_veto_cfg,
        sasang_veto_cfg_path=svp,
    )
    lines.extend(lg)
    v2p = myeongri_v2_upgrade_path or DEFAULT_MYEONGRI_V2_UPGRADE
    lv2, ok_v2 = _lines_myeongri_v2_upgrade(myeongri_v2_upgrade, v2p)
    lines.extend(lv2)
    lines.append("## 2) Hypothesis / insight ([HYPO] — not A-track trigger)")
    lines.append("")
    lines.append("| item | memo |")
    lines.append("|------|------|")
    lines.append("| hypothesis one-liner | *(operator)* |")
    lines.append("| next check script / artifact | *(operator)* |")
    lines.append("")
    lines.append("## 3) Final action (gate vocabulary only)")
    lines.append("")
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append("| `final_action_label` | *(operator)* |")
    ev_paths = (
        f"`{thin_path.as_posix()}`; `{fusion_path.as_posix()}`; "
        f"`{mp.as_posix()}`; `{mmp.as_posix()}`; `{crp.as_posix()}`; `{sp.as_posix()}`; `{sip.as_posix()}`; `{msp.as_posix()}`; "
        f"`{lp.as_posix()}`; `{atp.as_posix()}`; `{v2p.as_posix()}`"
    )
    lines.append(f"| `evidence_paths` | {ev_paths} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    ind_flags = {
        "myeongni": ok_m,
        "market_myeongni": ok_mm,
        "myeongni_conflict_runtime": ok_cr,
        "sasang": ok_s,
        "sasang_interpretive_bundle": ok_sib,
        "market_sasang": ok_ms,
        "logos_independent": ok_l,
        "governance_factlock": ok_g,
        "myeongri_v2_upgrade": ok_v2,
    }
    lines.append(
        "_Generator flags:_ "
        f"`thin_ok={thin_ok}` `calendar_pick={picked_date or 'fallback-or-none'}` "
        f"`fusion_ok={bool(narrative)}` "
        f"`independent_lens_ok={json.dumps(ind_flags, ensure_ascii=False)}`"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    p.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    p.add_argument("--thin-json", type=Path, default=DEFAULT_THIN)
    p.add_argument("--myeongni-json", type=Path, default=DEFAULT_MYEONGNI_LENS)
    p.add_argument("--sasang-json", type=Path, default=DEFAULT_SASANG_LENS)
    p.add_argument(
        "--sasang-interpretive-bundle-json",
        type=Path,
        default=DEFAULT_SASANG_INTERPRETIVE_BUNDLE,
    )
    p.add_argument("--market-sasang-json", type=Path, default=DEFAULT_MARKET_SASANG_LENS)
    p.add_argument("--market-myeongni-json", type=Path, default=DEFAULT_MARKET_MYEONGNI_LENS)
    p.add_argument("--logos-independent-json", type=Path, default=DEFAULT_LOGOS_INDEPENDENT_LENS)
    p.add_argument("--a-track-gonogo-json", type=Path, default=DEFAULT_A_TRACK_GONOGO)
    p.add_argument("--prophecy-monthly-json", type=Path, default=DEFAULT_PROPHECY_MONTHLY)
    p.add_argument("--lens-backtest-json", type=Path, default=DEFAULT_LENS_BACKTEST)
    p.add_argument("--myeongni-16state-json", type=Path, default=DEFAULT_MYEONGNI_16STATE)
    p.add_argument("--commander-myeongni-json", type=Path, default=DEFAULT_COMMANDER_MYEONGNI)
    p.add_argument("--sasang-veto-config-json", type=Path, default=DEFAULT_SASANG_VETO_CFG)
    p.add_argument(
        "--myeongri-v2-upgrade-json",
        type=Path,
        default=DEFAULT_MYEONGRI_V2_UPGRADE,
        help="myeongri_core_v2_upgrade_latest.json (run myeongri_core_v2_upgrade.py first).",
    )
    p.add_argument(
        "--myeongni-conflict-runtime-json",
        type=Path,
        default=DEFAULT_MYEONGNI_CONFLICT_RUNTIME,
        help="myeongni_conflict_arbitration_runtime_mode_latest.json (B-track policy stamp).",
    )
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument(
        "--brief-date-utc",
        default="",
        help="YYYY-MM-DD (UTC). Default: today's UTC date.",
    )
    p.add_argument("--workspace-anchor", default="BTC spot / operator anchor — set via CLI if needed")
    p.add_argument(
        "--calendar-date",
        default="",
        help="Prefer this calendar_date row in thin report (YYYY-MM-DD). Default: match brief-date, then last populated row.",
    )
    p.add_argument(
        "--also-dated-copy",
        action="store_true",
        help="Also write reports/daily_execution_insight_brief_YYYY-MM-DD.md",
    )
    args = p.parse_args()
    root = args.workspace_root.resolve()
    brief_date = args.brief_date_utc.strip() or _utc_date_today()
    cal = args.calendar_date.strip() or brief_date

    fusion_path = _abs_under_root(root, args.fusion_json)
    thin_path = _abs_under_root(root, args.thin_json)
    myeongni_path = _abs_under_root(root, args.myeongni_json)
    sasang_path = _abs_under_root(root, args.sasang_json)
    sasang_interpretive_bundle_path = _abs_under_root(root, args.sasang_interpretive_bundle_json)
    market_sasang_path = _abs_under_root(root, args.market_sasang_json)
    market_myeongni_path = _abs_under_root(root, args.market_myeongni_json)
    logos_independent_path = _abs_under_root(root, args.logos_independent_json)
    a_track_gonogo_path = _abs_under_root(root, args.a_track_gonogo_json)
    prophecy_monthly_path = _abs_under_root(root, args.prophecy_monthly_json)
    lens_backtest_path = _abs_under_root(root, args.lens_backtest_json)
    myeongni_16state_path = _abs_under_root(root, args.myeongni_16state_json)
    commander_myeongni_path = _abs_under_root(root, args.commander_myeongni_json)
    sasang_veto_cfg_path = _abs_under_root(root, args.sasang_veto_config_json)
    myeongri_v2_upgrade_path = _abs_under_root(root, args.myeongri_v2_upgrade_json)
    myeongni_conflict_runtime_path = _abs_under_root(root, args.myeongni_conflict_runtime_json)

    fusion = _read_json(fusion_path)
    thin = _read_json(thin_path)
    myeongni = _read_json(myeongni_path)
    sasang = _read_json(sasang_path)
    sasang_interpretive_bundle = _read_json(sasang_interpretive_bundle_path)
    market_sasang = _read_json(market_sasang_path)
    market_myeongni = _read_json(market_myeongni_path)
    logos_independent = _read_json(logos_independent_path)
    a_track_gonogo = _read_json(a_track_gonogo_path)
    prophecy_monthly = _read_json(prophecy_monthly_path)
    lens_backtest = _read_json(lens_backtest_path)
    myeongni_16state = _read_json(myeongni_16state_path)
    commander_myeongni = _read_json(commander_myeongni_path)
    sasang_veto_cfg = _read_json(sasang_veto_cfg_path)
    myeongri_v2_upgrade = _read_json(myeongri_v2_upgrade_path)
    myeongni_conflict_runtime = _read_json(myeongni_conflict_runtime_path)

    body = build_markdown(
        brief_date_utc=brief_date,
        workspace_anchor=args.workspace_anchor,
        fusion=fusion,
        thin=thin,
        thin_path=thin_path,
        fusion_path=fusion_path,
        calendar_date=cal,
        myeongni=myeongni,
        myeongni_path=myeongni_path,
        sasang=sasang,
        sasang_path=sasang_path,
        sasang_interpretive_bundle=sasang_interpretive_bundle,
        sasang_interpretive_bundle_path=sasang_interpretive_bundle_path,
        market_sasang=market_sasang,
        market_sasang_path=market_sasang_path,
        market_myeongni=market_myeongni,
        market_myeongni_path=market_myeongni_path,
        logos_independent=logos_independent,
        logos_independent_path=logos_independent_path,
        a_track_gonogo=a_track_gonogo,
        a_track_gonogo_path=a_track_gonogo_path,
        prophecy_monthly=prophecy_monthly,
        prophecy_monthly_path=prophecy_monthly_path,
        lens_backtest=lens_backtest,
        lens_backtest_path=lens_backtest_path,
        myeongni_16state=myeongni_16state,
        myeongni_16state_path=myeongni_16state_path,
        commander_myeongni=commander_myeongni,
        commander_myeongni_path=commander_myeongni_path,
        sasang_veto_cfg=sasang_veto_cfg,
        sasang_veto_cfg_path=sasang_veto_cfg_path,
        myeongri_v2_upgrade=myeongri_v2_upgrade,
        myeongri_v2_upgrade_path=myeongri_v2_upgrade_path,
        myeongni_conflict_runtime=myeongni_conflict_runtime,
        myeongni_conflict_runtime_path=myeongni_conflict_runtime_path,
    )

    out = args.out
    if not out.is_absolute():
        out = (root / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"WROTE: {out}")

    if args.also_dated_copy:
        dated = root / "reports" / f"daily_execution_insight_brief_{brief_date}.md"
        dated.parent.mkdir(parents=True, exist_ok=True)
        dated.write_text(body, encoding="utf-8")
        print(f"WROTE: {dated}")


if __name__ == "__main__":
    main()
