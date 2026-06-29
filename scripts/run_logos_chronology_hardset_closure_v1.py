#!/usr/bin/env python3
"""Post-sign-off closure: readiness + tier_v2 SSOT merge + human margin report ([HYPO])."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_chronology_hardset_closure_v1_latest.json"


def _run(cmd: list[str]) -> int:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return cp.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-merge", action="store_true", help="Skip tier_v2 SSOT merge refresh")
    args = ap.parse_args()

    steps: dict[str, int] = {}
    if not args.skip_merge:
        steps["tier_v2_ssot_merge"] = _run([PY, str(ROOT / "scripts/run_logos_chronology_tier_v2_ssot_merge_v1.py")])
    steps["signoff_readiness"] = _run([PY, str(ROOT / "scripts/check_logos_hardset_era_gold_signoff_readiness_v1.py")])
    steps["human_margin_report"] = _run([PY, str(ROOT / "scripts/build_logos_hardset_era_human_margin_report_v1.py")])
    steps["historical_tier_v2_ab"] = _run([PY, str(ROOT / "scripts/run_logos_chronology_historical_tier_v2_ab_v1.py")])
    steps["digest"] = _run([PY, str(ROOT / "scripts/build_logos_chronology_era_eval_digest_v1.py")])

    ok = all(code == 0 for code in steps.values())
    doc = {
        "schema": "logos_chronology_hardset_closure_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "ok": ok,
        "steps": steps,
        "outputs": [
            "reports/logos_hardset_era_human_margin_report_v1_latest.json",
            "reports/logos_hardset_era_human_margin_report_v1_latest.md",
            "reports/logos_chronology_era_blind_eval_digest_v1_latest.md",
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "steps": steps}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
