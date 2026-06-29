#!/usr/bin/env python3
"""One-shot Logos passive governance chain: lexicon smoke → eval refresh → governance digest.

  py scripts/run_logos_passive_drift_governance_chain_v1.py --fast
  py scripts/run_logos_passive_drift_governance_chain_v1.py --full

--fast: reuse existing holdout/off-fixture artifacts; refresh lexicon + governance + Track C anchor.
--full: also run summarize holdout + off-fixture AB (skip heavy v1/v2 re-eval unless --refresh-ab).
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
MANIFEST = ROOT / "reports/logos_passive_drift_governance_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(label: str, cmd: list[str]) -> dict[str, Any]:
    print(f"==> [{label}]", " ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=str(ROOT))
    return {"label": label, "exit_code": rc, "cmd": cmd}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fast", action="store_true", help="Skip eval refresh; governance from disk SSOT")
    ap.add_argument("--full", action="store_true", help="Refresh holdout + off-fixture summaries")
    ap.add_argument("--refresh-ab", action="store_true", help="With --full: rerun text_blind v1/v2 AB eval")
    args = ap.parse_args()
    if not args.fast and not args.full:
        args.fast = True

    py = sys.executable
    steps: dict[str, dict[str, Any]] = {}

    steps["lexicon_smoke"] = _run("lexicon_smoke", [py, str(ROOT / "scripts/check_lexicon_lookup_smoke_v1.py")])
    if steps["lexicon_smoke"]["exit_code"] != 0:
        _write_manifest(steps, ok=False)
        return 1

    if args.full:
        if args.refresh_ab:
            steps["text_blind_ab"] = _run(
                "text_blind_ab",
                [py, str(ROOT / "scripts/run_logos_chronology_text_blind_v2_ab_v1.py")],
            )
            if steps["text_blind_ab"]["exit_code"] != 0:
                _write_manifest(steps, ok=False)
                return 1
        steps["holdout_summarize"] = _run(
            "holdout_summarize",
            [py, str(ROOT / "scripts/summarize_logos_chronology_partition_holdout_v1.py")],
        )
        steps["off_fixture_ab"] = _run(
            "off_fixture_ab",
            [
                py,
                str(ROOT / "scripts/run_logos_chronology_off_fixture_text_blind_v2_ab_v1.py"),
                "--skip-gold-build",
            ],
        )
        for key in ("holdout_summarize", "off_fixture_ab"):
            if steps[key]["exit_code"] != 0:
                _write_manifest(steps, ok=False)
                return 1

    steps["governance"] = _run(
        "governance",
        [py, str(ROOT / "scripts/build_logos_passive_drift_governance_v1.py")],
    )
    steps["topology_anchor"] = _run(
        "topology_anchor",
        [py, str(ROOT / "scripts/build_logos_trackc_topology_radar_anchor_v1.py")],
    )

    ok = all(steps[k]["exit_code"] == 0 for k in ("governance", "topology_anchor"))
    _write_manifest(steps, ok=ok)
    return 0 if ok else 1


def _write_manifest(steps: dict[str, dict[str, Any]], *, ok: bool) -> None:
    doc = {
        "schema": "logos_passive_drift_governance_chain_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "steps": steps,
        "outputs": [
            "reports/lexicon_lookup_smoke_v1_latest.json",
            "docs/final/artifacts/logos_passive_drift_governance_v1_latest.json",
            "docs/final/artifacts/logos_passive_drift_governance_v1_latest.md",
            "docs/final/artifacts/logos_trackc_topology_radar_anchor_v1_latest.json",
            "reports/logos_passive_drift_governance_history.jsonl",
        ],
        "reproduce_fast": "py scripts/run_logos_passive_drift_governance_chain_v1.py --fast",
        "reproduce_full": "py scripts/run_logos_passive_drift_governance_chain_v1.py --full",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {MANIFEST}")


if __name__ == "__main__":
    raise SystemExit(main())
