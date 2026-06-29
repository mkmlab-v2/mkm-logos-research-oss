#!/usr/bin/env python3
"""RQ-028 A-code S2-Governor knob sim stub ([HYPO]).

Maps commander_profile (FACT anchors) + session myeongni panel row → measurable
orchestration knobs. No price, compression, or live trading outputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "experiments/a_code_12ai_v2/specs/a_code_12ai_matrix_v2.example.json"
DEFAULT_PATHOLOGY_MATRIX = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_2.json"
)
DEFAULT_SESSION_PANEL = ROOT / "reports/btrack_session_myeongni_panel_202606_june_prophecy.csv"
DEFAULT_MARKET_PSYCH = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"
DEFAULT_OUT = ROOT / "reports/a_code_governor_knob_sim_v1_latest.json"

FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "price_directional_hit_rate",
        "jaccard",
        "saving_pct",
        "predicted_direction",
        "actual_direction",
        "order_action",
        "live_trading",
        "dual_axis_beat",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _import_profile_resolver():
    path = ROOT / "scripts/a_code_commander_profile_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_profile_resolve", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import profile resolver: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_session_row(panel_csv: Path, session_date: str) -> dict[str, str]:
    rows = read_session_panel_rows(panel_csv)
    for row in rows:
        if str(row.get("session_local_date") or "") == session_date:
            return row
    raise ValueError(f"session_date not found in panel: {session_date}")


def read_session_panel_rows(panel_csv: Path) -> list[dict[str, str]]:
    with panel_csv.open(encoding="utf-8", newline="") as fh:
        rows = [dict(row) for row in csv.DictReader(fh)]
    return sorted(rows, key=lambda r: str(r.get("session_local_date") or ""))


def build_market_psych_hint_index(market_psych: Path | None) -> dict[str, str]:
    if market_psych is None or not market_psych.is_file():
        return {}
    doc = _load_json(market_psych)
    out: dict[str, str] = {}
    for row in doc.get("rows") or doc.get("per_date") or []:
        d = str(row.get("eval_date") or row.get("date") or "")
        if not d:
            continue
        bj = row.get("byungjeung") or {}
        out[d] = str(bj.get("transition_hint") or "stable_transition")
    return out


def _market_psych_hint(market_psych: Path | None, session_date: str) -> str | None:
    idx = build_market_psych_hint_index(market_psych)
    return idx.get(session_date)


def _pathology_gain_modifier(matrix: dict[str, Any], hint: str | None) -> float:
    if not hint:
        return 1.0
    mod = (matrix.get("hint_modifiers") or {}).get(hint) or {}
    return float(mod.get("pathology_gain", 1.0))


def _strength_parallel_penalty(strength: str) -> int:
    s = strength.strip()
    if s in {"중약", "신약", "극약"}:
        return 1
    return 0


def _sasang_lambda_bias(label: str) -> float:
    """Small deterministic bias from clinical_reference_only sasang label."""
    mapping = {
        "태양인": -0.02,
        "소양인": 0.0,
        "태음인": 0.02,
        "소음인": -0.01,
    }
    return mapping.get(label.strip(), 0.0)


def compute_knobs(
    *,
    matrix: dict[str, Any],
    profile: dict[str, Any],
    session_row: dict[str, str],
    pathology_matrix: dict[str, Any],
    transition_hint: str | None,
) -> dict[str, Any]:
    baseline = dict(matrix.get("governor_knobs") or {})
    base_lambda = float(baseline.get("token_budget_lambda", 0.25))
    base_parallel = int(baseline.get("parallel_cap", 2))
    base_path_cap = float(baseline.get("pathology_gain_cap", 0.76))

    imbalance = float(session_row.get("elem_imbalance") or 0.0)
    fire_share = float(session_row.get("elem_fire") or 0.0)
    metal_share = float(session_row.get("elem_metal") or 0.0)

    myeongni = profile.get("myeongni_fact_ref") or {}
    strength = str(myeongni.get("strength_label_engine") or "중약")
    sasang = profile.get("sasang_reference") or {}
    sasang_label = str(sasang.get("label") or "")

    hint_gain = _pathology_gain_modifier(pathology_matrix, transition_hint)
    lambda_adj = _clamp(
        base_lambda * (1.0 - 0.12 * imbalance) + _sasang_lambda_bias(sasang_label),
        0.10,
        0.50,
    )
    parallel_adj = int(
        _clamp(
            base_parallel - _strength_parallel_penalty(strength) - (1 if imbalance > 0.52 else 0),
            1,
            4,
        )
    )
    path_cap_adj = _clamp(
        base_path_cap * (1.0 - 0.08 * fire_share + 0.04 * metal_share) * max(0.85, min(1.15, hint_gain)),
        0.30,
        1.20,
    )

    adjusted = {
        "token_budget_lambda": round(lambda_adj, 4),
        "parallel_cap": parallel_adj,
        "pathology_gain_cap": round(path_cap_adj, 4),
    }
    delta = {
        "token_budget_lambda_delta": round(adjusted["token_budget_lambda"] - base_lambda, 4),
        "parallel_cap_delta": adjusted["parallel_cap"] - base_parallel,
        "pathology_gain_cap_delta": round(adjusted["pathology_gain_cap"] - base_path_cap, 4),
    }
    return {
        "baseline_knobs": {
            "token_budget_lambda": base_lambda,
            "parallel_cap": base_parallel,
            "pathology_gain_cap": base_path_cap,
        },
        "adjusted_knobs": adjusted,
        "governor_knob_delta": delta,
        "drivers": {
            "elem_imbalance": round(imbalance, 6),
            "elem_fire": round(fire_share, 6),
            "elem_metal": round(metal_share, 6),
            "strength_label_engine": strength,
            "sasang_reference_label": sasang_label,
            "transition_hint": transition_hint,
            "pathology_hint_gain": round(hint_gain, 4),
        },
    }


def _deterministic_fingerprint(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def run_sim(
    *,
    matrix: dict[str, Any],
    profile: dict[str, Any],
    session_row: dict[str, str],
    pathology_matrix: dict[str, Any],
    transition_hint: str | None,
    session_date: str,
) -> dict[str, Any]:
    knob_block = compute_knobs(
        matrix=matrix,
        profile=profile,
        session_row=session_row,
        pathology_matrix=pathology_matrix,
        transition_hint=transition_hint,
    )
    replay_payload = {
        "session_date": session_date,
        "adjusted_knobs": knob_block["adjusted_knobs"],
        "drivers": knob_block["drivers"],
    }
    fp1 = _deterministic_fingerprint(replay_payload)
    fp2 = _deterministic_fingerprint(replay_payload)
    orchestration_consistency = fp1 == fp2

    report = {
        "schema": "a_code_governor_knob_sim_report_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-028",
        "hypothesis_tier": "B",
        "research_only": True,
        "cell_id": "S2-Governor",
        "session_date": session_date,
        "session_pillars": {
            "year": session_row.get("year_pillar"),
            "month": session_row.get("month_pillar"),
            "day": session_row.get("day_pillar"),
            "hour": session_row.get("hour_pillar"),
        },
        "commander_anchors": {
            "day_master_stem": (profile.get("myeongni_fact_ref") or {}).get("day_master_stem"),
            "strength_label_engine": (profile.get("myeongni_fact_ref") or {}).get("strength_label_engine"),
            "sasang_reference_label": (profile.get("sasang_reference") or {}).get("label"),
            "sasang_rail": (profile.get("sasang_reference") or {}).get("rail"),
        },
        **knob_block,
        "eval_axes": {
            "governor_knob_delta": knob_block["governor_knob_delta"],
            "orchestration_consistency": orchestration_consistency,
            "deterministic_fingerprint": fp1,
        },
        "note_ko": "S2 노브 시뮬. Track A·실매매·임상 게이팅과 자동 합선 금지.",
    }
    return report


def _assert_no_forbidden_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"forbidden output key at {path}.{k}")
            _assert_no_forbidden_keys(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_forbidden_keys(item, f"{path}[{i}]")


def main() -> int:
    parser = argparse.ArgumentParser(description="A-code S2-Governor knob sim stub (RQ-028)")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--profile", type=Path, default=None, help="default: local > MKM_COMMANDER_PROFILE_JSON > example")
    parser.add_argument("--pathology-matrix", type=Path, default=DEFAULT_PATHOLOGY_MATRIX)
    parser.add_argument("--session-panel", type=Path, default=DEFAULT_SESSION_PANEL)
    parser.add_argument("--session-date", type=str, default=None, help="YYYY-MM-DD (default: today UTC date)")
    parser.add_argument("--market-psych", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    session_date = args.session_date or date.today().isoformat()
    matrix = _load_json(args.matrix)
    resolver = _import_profile_resolver()
    profile_path, profile_source = resolver.resolve_commander_profile_path(args.profile)
    profile = _load_json(profile_path)
    pathology_matrix = _load_json(args.pathology_matrix)
    session_row = _read_session_row(args.session_panel, session_date)
    transition_hint = _market_psych_hint(args.market_psych, session_date)

    report = run_sim(
        matrix=matrix,
        profile=profile,
        session_row=session_row,
        pathology_matrix=pathology_matrix,
        transition_hint=transition_hint,
        session_date=session_date,
    )
    report["profile_path"] = str(profile_path.relative_to(ROOT)).replace("\\", "/")
    report["profile_source"] = profile_source
    _assert_no_forbidden_keys(report)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out}")
    print(
        "knobs:",
        report["adjusted_knobs"],
        "delta:",
        report["governor_knob_delta"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
