#!/usr/bin/env python3
"""Build baseline report for Vibe-Trading B-Track sandbox."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
VIBE = ROOT / "research" / "vibe_trading_btrack_sandbox" / "Vibe-Trading"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def safe_get(d: dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def count_glob(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    return len(list(path.glob(pattern)))


def main() -> int:
    prophecy = load_json(ART / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json")
    governance = load_json(ART / "integrated_governance_v1_latest.json")
    go_nogo = load_json(ART / "a_track_go_nogo_status_latest.json")

    skills_dir = VIBE / "agent" / "src" / "skills"
    presets_dir = VIBE / "agent" / "src" / "swarm" / "presets"
    engines_dir = VIBE / "agent" / "backtest" / "engines"
    optimizers_dir = VIBE / "agent" / "backtest" / "optimizers"
    loaders_dir = VIBE / "agent" / "backtest" / "loaders"

    report = {
        "schema": "vibe_btrack_baseline_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "research_only",
        "btrack_guardrail": "no_auto_bridge_to_track_a",
        "vibe_repo": {
            "path": str(VIBE).replace("\\", "/"),
            "exists": VIBE.exists(),
            "skills_count": count_glob(skills_dir, "*/SKILL.md"),
            "swarm_presets_count": count_glob(presets_dir, "*.yaml"),
            "backtest_engines_count": count_glob(engines_dir, "*.py"),
            "backtest_optimizers_count": count_glob(optimizers_dir, "*.py"),
            "backtest_loaders_count": count_glob(loaders_dir, "*.py"),
        },
        "mkm_baseline": {
            "prophecy_path": "docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json",
            "integrated_governance_path": "docs/final/artifacts/integrated_governance_v1_latest.json",
            "a_track_path": "docs/final/artifacts/a_track_go_nogo_status_latest.json",
            "high_reliability_decision": safe_get(prophecy, "meta", "high_reliability_decision"),
            "price_output_locked": safe_get(prophecy, "meta", "price_output_locked"),
            "risk_profile_mode": safe_get(prophecy, "risk_profile", "mode"),
            "final_regime": safe_get(governance, "final_regime"),
            "final_score": safe_get(governance, "final_score"),
            "overall_go_no_go": safe_get(go_nogo, "result", "overall_go_no_go"),
            "recommended_stage": safe_get(go_nogo, "result", "recommended_stage"),
            "failed_reasons": safe_get(go_nogo, "result", "failed_reasons"),
        },
        "decision": {
            "track": "B",
            "action": "continue_shadow_research",
            "note": "Use Vibe as research copilot only; reimplement candidates in MKM SSOT before any promotion."
        },
    }

    out_json = ART / "vibe_btrack_baseline_report_latest.json"
    out_md = ART / "vibe_btrack_baseline_report_latest.md"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Vibe B-Track Baseline Report (Latest)",
        "",
        f"- Generated (UTC): {report['generated_at_utc']}",
        f"- Scope: {report['scope']}",
        "",
        "## Vibe Repository Scan",
        f"- Path exists: {report['vibe_repo']['exists']}",
        f"- Skills (SKILL.md): {report['vibe_repo']['skills_count']}",
        f"- Swarm presets (*.yaml): {report['vibe_repo']['swarm_presets_count']}",
        f"- Backtest engines (*.py): {report['vibe_repo']['backtest_engines_count']}",
        f"- Backtest optimizers (*.py): {report['vibe_repo']['backtest_optimizers_count']}",
        f"- Backtest loaders (*.py): {report['vibe_repo']['backtest_loaders_count']}",
        "",
        "## MKM Baseline (Fact-Lock)",
        f"- high_reliability_decision: {report['mkm_baseline']['high_reliability_decision']}",
        f"- price_output_locked: {report['mkm_baseline']['price_output_locked']}",
        f"- risk_profile_mode: {report['mkm_baseline']['risk_profile_mode']}",
        f"- final_regime: {report['mkm_baseline']['final_regime']}",
        f"- final_score: {report['mkm_baseline']['final_score']}",
        f"- overall_go_no_go: {report['mkm_baseline']['overall_go_no_go']}",
        f"- recommended_stage: {report['mkm_baseline']['recommended_stage']}",
        f"- failed_reasons: {report['mkm_baseline']['failed_reasons']}",
        "",
        "## Decision",
        "- Track: B only",
        "- Action: continue_shadow_research",
        "- Guardrail: no auto-bridge to Track A",
        "",
    ]
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"written: {out_json}")
    print(f"written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

