#!/usr/bin/env python3
"""RQ-028 P5: evening 1-line A-code S2 governor knob observation ([HYPO], non-gating)."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "experiments/a_code_12ai_v2/specs/a_code_12ai_matrix_v2.example.json"
DEFAULT_PATHOLOGY = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_2.json"
)
DEFAULT_SESSION_PANEL = ROOT / "reports/btrack_session_myeongni_panel_202606_june_prophecy.csv"
DEFAULT_MARKET_PSYCH = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"
DEFAULT_OUT = ROOT / "reports/a_code_governor_knob_evening_observation_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _kst_today() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()


def _import_resolver():
    path = ROOT / "scripts/a_code_commander_profile_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_profile_resolve", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import profile resolver: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_governor_sim():
    path = ROOT / "scripts/run_a_code_governor_knob_sim_stub_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_governor_sim", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import governor sim: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["a_code_governor_sim"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _evening_line(
    *,
    session_date: str,
    day_pillar: str,
    knobs: dict[str, Any],
    delta: dict[str, Any],
    profile_source: str,
    transition_hint: str | None,
) -> str:
    lam = knobs.get("token_budget_lambda")
    par = knobs.get("parallel_cap")
    cap = knobs.get("pathology_gain_cap")
    hint = transition_hint or "none"
    return (
        f"▸ A-code S2 [HYPO·non-gating]: λ={lam} parallel={par} path_cap={cap} "
        f"Δλ={delta.get('token_budget_lambda_delta')} · {session_date} {day_pillar} · "
        f"profile={profile_source} · hint={hint} · WATCH only"
    )


def build(
    *,
    matrix: dict[str, Any],
    profile: dict[str, Any],
    profile_path: Path,
    profile_source: str,
    session_row: dict[str, str],
    pathology_matrix: dict[str, Any],
    transition_hint: str | None,
    session_date: str,
) -> dict[str, Any]:
    sim = _import_governor_sim()
    report = sim.run_sim(
        matrix=matrix,
        profile=profile,
        session_row=session_row,
        pathology_matrix=pathology_matrix,
        transition_hint=transition_hint,
        session_date=session_date,
    )
    knobs = report["adjusted_knobs"]
    delta = report["governor_knob_delta"]
    day_pillar = str(session_row.get("day_pillar") or report.get("session_pillars", {}).get("day") or "")
    line = _evening_line(
        session_date=session_date,
        day_pillar=day_pillar,
        knobs=knobs,
        delta=delta,
        profile_source=profile_source,
        transition_hint=transition_hint,
    )
    return {
        "schema": "a_code_governor_knob_evening_observation_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-028",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "cell_id": "S2-Governor",
        "session_date": session_date,
        "profile_path": str(profile_path.relative_to(ROOT)).replace("\\", "/"),
        "profile_source": profile_source,
        "evening_append_line": line,
        "adjusted_knobs": knobs,
        "governor_knob_delta": delta,
        "session_pillars": report.get("session_pillars"),
        "drivers": report.get("drivers"),
        "eval_axes": {
            "governor_knob_delta": delta,
            "orchestration_consistency": (report.get("eval_axes") or {}).get("orchestration_consistency"),
        },
        "track_wall": {
            "track_a_trading": "no_auto_promotion",
            "live_trading_gate": "no_trigger",
            "note_ko": "evening 관측 1줄만; 주문·승격·Track A 합선 없음",
        },
        "note_ko": "코스피 evening 루프 관측용. 트리거·게이팅 아님.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="A-code governor knob evening observation (1-line)")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--profile", type=Path, default=None)
    parser.add_argument("--pathology-matrix", type=Path, default=DEFAULT_PATHOLOGY)
    parser.add_argument("--session-panel", type=Path, default=DEFAULT_SESSION_PANEL)
    parser.add_argument("--session-date", type=str, default=None, help="YYYY-MM-DD (default: Asia/Seoul today)")
    parser.add_argument("--market-psych", type=Path, default=DEFAULT_MARKET_PSYCH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    resolver = _import_resolver()
    profile_path, profile_source = resolver.resolve_commander_profile_path(args.profile)
    session_date = args.session_date or _kst_today()

    sim = _import_governor_sim()
    matrix = _load(args.matrix)
    profile = _load(profile_path)
    pathology_matrix = _load(args.pathology_matrix)
    session_row = sim._read_session_row(args.session_panel, session_date)
    transition_hint = sim._market_psych_hint(args.market_psych, session_date)

    doc = build(
        matrix=matrix,
        profile=profile,
        profile_path=profile_path,
        profile_source=profile_source,
        session_row=session_row,
        pathology_matrix=pathology_matrix,
        transition_hint=transition_hint,
        session_date=session_date,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out}")
    print(doc["evening_append_line"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
