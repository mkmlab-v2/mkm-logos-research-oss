#!/usr/bin/env python3
"""Oracle narrative + closure observability chain (read-only) [HYPO].

  py scripts/run_logos_oracle_narrative_closure_observability_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json"
REPORT = ROOT / "reports/logos_oracle_narrative_closure_observability_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    return int(proc.returncode or 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-drift-compare", action="store_true")
    ap.add_argument("--skip-passive-drift", action="store_true")
    ap.add_argument("--skip-readiness", action="store_true")
    ap.add_argument("--skip-vocology", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_drift_compare:
        code = _run(
            [
                sys.executable,
                "scripts/build_logos_lemma_spike_drift_snapshot_v1.py",
                "--compare",
            ]
        )
        steps.append({"step": "lemma_spike_drift_compare", "exit_code": code})
        if code != 0:
            return code

    if not args.skip_passive_drift:
        code = _run(
            [
                sys.executable,
                "scripts/run_logos_passive_drift_governance_chain_v1.py",
                "--fast",
            ]
        )
        steps.append({"step": "passive_drift_governance_fast", "exit_code": code})
        if code != 0:
            return code

    if not args.skip_vocology:
        for label, script in (
            ("voc_validate", "scripts/validate_han_vocology_km_vhi_pilot_jsonl_v1.py"),
            ("voc_closure", "scripts/build_han_vocology_pilot_closure_v1.py"),
        ):
            cmd = [sys.executable, script]
            if label == "voc_closure":
                cmd.append("--skip-validate")
            code = _run(cmd)
            steps.append({"step": label, "exit_code": code})
            if code != 0:
                return code

    if not args.skip_readiness:
        readiness_cmd = [
            sys.executable,
            "scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py",
            "--skip-overlay-refresh",
        ]
        if args.skip_pytest:
            readiness_cmd.append("--skip-pytest")
        code = _run(readiness_cmd)
        steps.append({"step": "tier1_tier2_readiness", "exit_code": code})
        if code != 0:
            return code

    code = _run([sys.executable, "scripts/build_logos_oracle_narrative_closure_observability_v1.py"])
    steps.append({"step": "build_observability", "exit_code": code})
    if code != 0:
        return code

    if not args.skip_pytest:
        code = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_oracle_narrative_closure_observability_v1.py",
                "-q",
            ]
        )
        if code != 0:
            return code

    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    report = {
        "schema": "logos_oracle_narrative_closure_observability_chain_v1",
        "chain_pass": doc.get("observation_pass") is True,
        "generated_at_utc": _utc(),
        "research_only": True,
        "observation_artifact": str(OUT.relative_to(ROOT)),
        "steps": steps,
        "repro_one_shot": "py scripts/run_logos_oracle_narrative_closure_observability_chain_v1.py",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"chain_pass={report['chain_pass']} observations={doc.get('observations_pass_count')}/{doc.get('observations_total')}")
    return 0 if report["chain_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
