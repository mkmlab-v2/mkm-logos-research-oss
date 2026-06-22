#!/usr/bin/env python3
"""Gate check for universal_root_topology_crosswalk vs TOPOLOGY_CROSSWALK_SPEC [HYPO]."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports/universal_root_topology_crosswalk_v1_latest.json"
DEFAULT_SPEC = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json"
DEFAULT_OUT = ROOT / "reports/universal_root_topology_crosswalk_gate_v1_latest.json"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evaluate_gate(report: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    thr = spec.get("thresholds") or {}
    summary = report.get("summary") or {}
    topo = report.get("topology_plane") or {}
    wall = report.get("wall_divergence") or {}

    pair_count = int(summary.get("pair_count") or topo.get("pair_count") or 0)
    reachable = topo.get("verse_reachable_rate")
    lex_only_rate = wall.get("lexicon_only_without_topology_rate")
    neg_leaks = int(topo.get("negative_topology_leak_count") or 0)
    plane_sep = bool(wall.get("plane_separation_reported"))
    collapsed = wall.get("collapsed_combined_score")

    checks = [
        {
            "name": "fixture_pair_count_min",
            "ok": pair_count >= int(thr.get("fixture_pair_count_min", 500)),
            "observed": pair_count,
            "threshold": thr.get("fixture_pair_count_min", 500),
        },
        {
            "name": "min_verse_reachable_rate",
            "ok": reachable is not None and float(reachable) >= float(thr.get("min_verse_reachable_rate", 0.5)),
            "observed": reachable,
            "threshold": thr.get("min_verse_reachable_rate", 0.5),
        },
        {
            "name": "max_lexicon_only_without_topology_rate",
            "ok": lex_only_rate is not None
            and float(lex_only_rate) <= float(thr.get("max_lexicon_only_without_topology_rate", 0.02)),
            "observed": lex_only_rate,
            "threshold": thr.get("max_lexicon_only_without_topology_rate", 0.02),
        },
        {
            "name": "max_negative_topology_leak_count",
            "ok": neg_leaks <= int(thr.get("max_negative_topology_leak_count", 0)),
            "observed": neg_leaks,
            "threshold": thr.get("max_negative_topology_leak_count", 0),
        },
        {
            "name": "require_plane_separation_report",
            "ok": plane_sep and collapsed is None,
            "observed": {"plane_separation_reported": plane_sep, "collapsed_combined_score": collapsed},
            "threshold": True,
        },
    ]
    return {"gate_ok": all(c["ok"] for c in checks), "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.report.is_file():
        print(json.dumps({"ok": False, "error": "missing_crosswalk_report"}))
        return 2

    report = _read(args.report)
    spec = _read(args.spec) if args.spec.is_file() else {}
    gate = evaluate_gate(report, spec)
    out_doc = {
        "schema": "universal_root_topology_crosswalk_gate_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "report_pointer": str(args.report.relative_to(ROOT)).replace("\\", "/"),
        "spec_pointer": str(args.spec.relative_to(ROOT)).replace("\\", "/") if args.spec.is_file() else None,
        **gate,
        "reproduce": "py scripts/check_universal_root_topology_crosswalk_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": gate["gate_ok"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if gate["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
