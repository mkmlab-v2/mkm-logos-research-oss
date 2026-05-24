#!/usr/bin/env python3
"""[HYPO] Fuse parallel 10-lane summary + weekly review pack + lens fusion stub."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_parallel_weekly_fusion_v1_latest.json"
PARALLEL_SUMMARY = ROOT / "reports/btrack_parallel_run_summary_v1_latest.json"
WEEKLY_PACK = ROOT / "reports/btrack_weekly_prophecy_review_pack_v1_latest.json"
FUSION_STUB = ROOT / "docs/final/artifacts/independent_lens_fusion_stub_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(p)


def build(*, run_fusion_stub: bool) -> dict[str, Any]:
    py = sys.executable
    subprocess.run([py, "scripts/build_btrack_parallel_run_summary_v1.py"], cwd=str(ROOT), check=True)
    if run_fusion_stub:
        subprocess.run([py, "scripts/report_independent_lens_fusion_stub_v0.py"], cwd=str(ROOT), check=True)

    parallel = _load(PARALLEL_SUMMARY) or {}
    weekly = _load(WEEKLY_PACK) or {}
    stub = _load(FUSION_STUB) or {}

    operator_lines = list(parallel.get("operator_lines") or [])
    operator_lines.extend(weekly.get("operator_lines") or [])
    consensus = stub.get("consensus") or stub.get("summary") or {}
    if stub:
        operator_lines.append(
            f"- [MKM-PAR-FUSE] Lens fusion stub: {stub.get('consensus_label') or stub.get('status') or 'see artifact'}"
        )

    return {
        "schema": "btrack_parallel_weekly_fusion_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "parallel_summary": {
            "artifact": _rel(PARALLEL_SUMMARY),
            "instrument_split": parallel.get("instrument_split"),
            "policy": parallel.get("policy"),
            "lanes": parallel.get("lanes"),
        },
        "weekly_review_pack": {
            "artifact": _rel(WEEKLY_PACK) if weekly else None,
            "headline_frozen_kpi_a": weekly.get("headline_frozen_kpi_a"),
            "operator_lines": weekly.get("operator_lines"),
        },
        "independent_lens_fusion_stub": {
            "artifact": _rel(FUSION_STUB) if stub else None,
            "consensus": consensus,
        },
        "track_a_live_promotion": False,
        "boundary_ack": (
            "Fused read-only view. Lane SSOT remains per JSON. "
            "KOSPI/BTC parallel lanes must not overwrite btrack_hypothesis_prophecy_latest.json."
        ),
        "operator_lines": operator_lines,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-fusion-stub", action="store_true")
    args = ap.parse_args()
    doc = build(run_fusion_stub=not args.skip_fusion_stub)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
