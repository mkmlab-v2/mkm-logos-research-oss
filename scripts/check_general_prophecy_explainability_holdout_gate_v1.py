#!/usr/bin/env python3
"""Gate checker for explainability holdout stability (B-track)."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_explainability_holdout_report_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_explainability_holdout_gate_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--profile", choices=("research", "ops"), default="research")
    ap.add_argument("--min-holdout-direct-rate", type=float, default=None)
    ap.add_argument("--min-holdout-repro-rate", type=float, default=None)
    ap.add_argument("--min-holdout-coverage", type=float, default=None)
    ap.add_argument("--strict-exit", action="store_true", help="Exit 2 on breach")
    args = ap.parse_args()

    if not args.holdout_json.is_file():
        raise SystemExit(f"Missing --holdout-json: {args.holdout_json}")

    doc = _read_json(args.holdout_json)
    holdout = doc.get("holdout_core") if isinstance(doc.get("holdout_core"), dict) else {}
    n_holdout = int(holdout.get("n_questions") or 0)
    direct = _f(holdout.get("direct_match_rate"))
    repro = _f(holdout.get("reproducible_evidence_rate"))
    cov = _f(holdout.get("avg_biblical_keyword_coverage"))

    profile_thresholds = {
        "research": {"min_holdout_direct_rate": 0.7, "min_holdout_repro_rate": 0.9, "min_holdout_coverage": 0.3},
        "ops": {"min_holdout_direct_rate": 0.85, "min_holdout_repro_rate": 0.95, "min_holdout_coverage": 0.35},
    }
    t = profile_thresholds[args.profile]
    min_direct = float(args.min_holdout_direct_rate) if args.min_holdout_direct_rate is not None else t["min_holdout_direct_rate"]
    min_repro = float(args.min_holdout_repro_rate) if args.min_holdout_repro_rate is not None else t["min_holdout_repro_rate"]
    min_cov = float(args.min_holdout_coverage) if args.min_holdout_coverage is not None else t["min_holdout_coverage"]

    checks = {
        "min_holdout_questions_pass": n_holdout >= 1,
        "min_holdout_direct_rate_pass": bool(direct is not None and direct >= min_direct),
        "min_holdout_repro_rate_pass": bool(repro is not None and repro >= min_repro),
        "min_holdout_coverage_pass": bool(cov is not None and cov >= min_cov),
    }
    all_pass = all(checks.values())

    decision = "GO_HOLDOUT_STABLE" if all_pass else "WARN_HOLDOUT_DRIFT_RISK"
    out = {
        "schema": "general_prophecy_explainability_holdout_gate_v1",
        "generated_at_utc": _utc_now(),
        "source_holdout_report": str(args.holdout_json).replace("\\", "/"),
        "profile": args.profile,
        "thresholds": {
            "min_holdout_direct_rate": min_direct,
            "min_holdout_repro_rate": min_repro,
            "min_holdout_coverage": min_cov,
        },
        "metrics_snapshot": {
            "holdout_n_questions": n_holdout,
            "holdout_direct_match_rate": direct,
            "holdout_reproducible_evidence_rate": repro,
            "holdout_avg_biblical_keyword_coverage": cov,
        },
        "checks": checks,
        "all_pass": all_pass,
        "decision": decision,
        "track_wall": {
            "source_track": "B",
            "research_only": True,
            "auto_bridge_to_a_track": False,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "all_pass": all_pass}, ensure_ascii=False))

    strict = args.strict_exit or _truthy_env("MKM_GENERAL_PROPHECY_HOLDOUT_GATE_STRICT_EXIT")
    if strict and not all_pass:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
