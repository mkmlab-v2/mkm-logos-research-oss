#!/usr/bin/env python3
"""Parameter-only evolution sweep for Field×Logos overlay lane (allowlist rail)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evolution_auto_apply_allowlist_v1 import load_allowlist  # noqa: E402
from field_logos_overlay_prophecy_common_v1 import DEFAULT_OVERLAY_OUT, read_json  # noqa: E402

BUILD = ROOT / "scripts/build_field_logos_overlay_prophecy_v1.py"
EVAL = ROOT / "scripts/eval_field_logos_overlay_prophecy_v1.py"
DEFAULT_SWEEP_OUT = ROOT / "reports/field_logos_overlay_evolution_sweep_v1_latest.json"
DEFAULT_RECOMMENDED = ROOT / "reports/field_logos_overlay_recommended_params_v1_latest.json"

ALLOWED_PARAMS = frozenset({"overlay_weight", "theme_match_threshold", "logos_resonance_min_cosine"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _assert_rail() -> None:
    doc = load_allowlist()
    rails = doc.get("rails") if isinstance(doc.get("rails"), dict) else {}
    block = rails.get("field_logos_overlay") if isinstance(rails.get("field_logos_overlay"), dict) else {}
    mode = str(block.get("auto_apply_mode") or "")
    if mode != "parameter_only":
        raise ValueError(f"field_logos_overlay rail auto_apply_mode must be parameter_only, got {mode!r}")
    allowed = frozenset(str(x) for x in (block.get("allowed_parameter_targets") or []))
    if not ALLOWED_PARAMS.issubset(allowed):
        raise ValueError(f"allowlist missing parameter targets: {sorted(ALLOWED_PARAMS - allowed)}")


def _run_build_eval(
    *,
    overlay_weight: float,
    theme_match_threshold: float,
    logos_resonance_min_cosine: float,
    overlay_out: Path,
    eval_out: Path,
) -> tuple[float, dict[str, Any] | None]:
    cp1 = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--overlay-weight",
            str(overlay_weight),
            "--theme-match-threshold",
            str(theme_match_threshold),
            "--logos-resonance-min-cosine",
            str(logos_resonance_min_cosine),
            "--output-json",
            str(overlay_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if cp1.returncode != 0:
        return -1.0, None
    cp2 = subprocess.run(
        [sys.executable, str(EVAL), "--overlay-json", str(overlay_out), "--output-json", str(eval_out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if cp2.returncode != 0:
        return -1.0, read_json(eval_out)
    ev = read_json(eval_out)
    if not ev:
        return -1.0, None
    return float((ev.get("summary") or {}).get("pass_rate") or 0.0), ev


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_SWEEP_OUT)
    ap.add_argument("--recommended-json", type=Path, default=DEFAULT_RECOMMENDED)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    _assert_rail()

    grid = [
        {"overlay_weight": ow, "theme_match_threshold": tt, "logos_resonance_min_cosine": lc}
        for ow in (0.25, 0.35, 0.5)
        for tt in (0.4, 0.5, 0.6)
        for lc in (0.0, 0.75)
    ]

    trials: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    best_rate = -1.0

    if args.dry_run:
        doc = {
            "schema": "field_logos_overlay_evolution_sweep_v1",
            "generated_at_utc": _utc_now(),
            "dry_run": True,
            "grid_size": len(grid),
            "research_only": True,
            "track_wall": {"auto_apply": "parameter_only", "live_trading": False},
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True, "grid_size": len(grid)}, ensure_ascii=False))
        return 0

    tmp_overlay = ROOT / "reports/_tmp_field_logos_overlay_sweep.json"
    tmp_eval = ROOT / "reports/_tmp_field_logos_overlay_sweep_eval.json"

    for params in grid:
        rate, ev = _run_build_eval(
            overlay_weight=params["overlay_weight"],
            theme_match_threshold=params["theme_match_threshold"],
            logos_resonance_min_cosine=params["logos_resonance_min_cosine"],
            overlay_out=tmp_overlay,
            eval_out=tmp_eval,
        )
        row = {**params, "pass_rate": rate, "eval_ok": bool((ev or {}).get("summary", {}).get("eval_ok"))}
        trials.append(row)
        if rate > best_rate:
            best_rate = rate
            best = row

    sweep_doc = {
        "schema": "field_logos_overlay_evolution_sweep_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "rail": "field_logos_overlay",
        "auto_apply_mode": "parameter_only",
        "trials": trials,
        "best": best,
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
        },
    }
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sweep_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if best:
        recommended = {
            "schema": "field_logos_overlay_recommended_params_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "parameters": {
                "overlay_weight": best["overlay_weight"],
                "theme_match_threshold": best["theme_match_threshold"],
                "logos_resonance_min_cosine": best["logos_resonance_min_cosine"],
            },
            "pass_rate": best_rate,
            "sweep_path": str(out.relative_to(ROOT)).replace("\\", "/"),
            "applied_to": str(DEFAULT_OVERLAY_OUT.relative_to(ROOT)).replace("\\", "/"),
        }
        rec_path = args.recommended_json if args.recommended_json.is_absolute() else ROOT / args.recommended_json
        rec_path.parent.mkdir(parents=True, exist_ok=True)
        rec_path.write_text(json.dumps(recommended, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(BUILD),
                "--overlay-weight",
                str(best["overlay_weight"]),
                "--theme-match-threshold",
                str(best["theme_match_threshold"]),
                "--logos-resonance-min-cosine",
                str(best["logos_resonance_min_cosine"]),
                "--output-json",
                str(DEFAULT_OVERLAY_OUT),
            ],
            cwd=str(ROOT),
            check=False,
        )
        subprocess.run(
            [sys.executable, str(EVAL), "--overlay-json", str(DEFAULT_OVERLAY_OUT)],
            cwd=str(ROOT),
            check=False,
        )

    print(json.dumps({"ok": True, "best_pass_rate": best_rate, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
