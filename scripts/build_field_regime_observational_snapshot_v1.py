#!/usr/bin/env python3
"""Build Field (1st regime_map) observational snapshot for ops closure [HYPO].

Primary live regime attachment is out of scope; this aggregates B-track chronology match
and optional Quad-Fusion year ranking when inputs exist. Does NOT trigger live trading.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHRONO_OUT = ROOT / "reports/constitution/btrack_pilot/chronology_regime_match_v1_latest.json"
DEFAULT_QUAD_OUT = ROOT / "reports/field_regime_quad_rank_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/field_regime_observational_snapshot_v1_latest.json"
DEFAULT_QUAD_JSON = ROOT / "data/quad_fusion_training/quad_fusion_result_20260308_230751.json"
RANK_SCRIPT = ROOT / "scripts/rank_quad_timeline_year_vs_regime_fingerprints.py"
CHRONO_SCRIPT = ROOT / "scripts/build_chronology_regime_match_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _run_chronology(out_path: Path) -> tuple[int, dict[str, Any] | None]:
    if not CHRONO_SCRIPT.is_file():
        return 2, None
    proc = subprocess.run(
        [sys.executable, str(CHRONO_SCRIPT), "--output-json", str(out_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, _read_json(out_path)


def _run_quad_rank(year: int, quad_json: Path, out_path: Path) -> tuple[int, dict[str, Any] | None]:
    if not RANK_SCRIPT.is_file() or not quad_json.is_file():
        return 2, None
    proc = subprocess.run(
        [
            sys.executable,
            str(RANK_SCRIPT),
            "--year",
            str(year),
            "--quad-json",
            str(quad_json),
            "--output",
            str(out_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, _read_json(out_path)


def build_snapshot(*, year: int, quad_json: Path, chrono_out: Path, quad_out: Path) -> dict[str, Any]:
    chrono_rc, chrono = _run_chronology(chrono_out)
    quad_rc, quad = _run_quad_rank(year, quad_json, quad_out)

    primary_regime: str | None = None
    primary_source = "none"
    if quad and quad.get("primary_historical_regime"):
        primary_regime = str(quad["primary_historical_regime"])
        primary_source = "quad_timeline_year_vs_regime_fingerprints_v1"
    elif chrono and chrono.get("primary_regime_map_observational"):
        primary_regime = str(chrono["primary_regime_map_observational"])
        primary_source = "chronology_regime_match_v1_fallback"

    doc: dict[str, Any] = {
        "schema": "field_regime_observational_snapshot_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "[HYPO]",
        "interpretation_class": "[HYPO]",
        "non_gating": True,
        "track_wall": {
            "a_track_auto_promotion": False,
            "live_trading_trigger": False,
            "logos_secondary_only": True,
        },
        "field_layer": {
            "primary_regime_id_observational": primary_regime,
            "primary_source": primary_source,
            "live_regime_attached": False,
            "operator_hint_ko": (
                "1차 Field=regime_map 실물 주(主). 본 스냅샷은 관측·연구용이며 "
                "실전 트리거·Track A 자동 합선 금지."
            ),
        },
        "lanes": {
            "chronology_regime_match": {
                "exit_code": chrono_rc,
                "path": _rel_path(chrono_out) if chrono else None,
                "top_match_id": (chrono.get("top_match") or {}).get("match_id") if chrono else None,
                "disagreement_index": chrono.get("disagreement_index") if chrono else None,
            },
            "quad_timeline_rank": {
                "exit_code": quad_rc,
                "path": _rel_path(quad_out) if quad else None,
                "year": year,
                "primary_historical_regime": quad.get("primary_historical_regime") if quad else None,
                "quad_json_present": quad_json.is_file(),
            },
        },
    }
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Field regime observational snapshot v1")
    ap.add_argument("--year", type=int, default=datetime.now().year)
    ap.add_argument("--quad-json", type=Path, default=DEFAULT_QUAD_JSON)
    ap.add_argument("--chrono-out", type=Path, default=DEFAULT_CHRONO_OUT)
    ap.add_argument("--quad-out", type=Path, default=DEFAULT_QUAD_OUT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = build_snapshot(
        year=args.year,
        quad_json=args.quad_json if args.quad_json.is_absolute() else ROOT / args.quad_json,
        chrono_out=args.chrono_out if args.chrono_out.is_absolute() else ROOT / args.chrono_out,
        quad_out=args.quad_out if args.quad_out.is_absolute() else ROOT / args.quad_out,
    )
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "wrote": str(out), "primary": doc["field_layer"]["primary_regime_id_observational"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
