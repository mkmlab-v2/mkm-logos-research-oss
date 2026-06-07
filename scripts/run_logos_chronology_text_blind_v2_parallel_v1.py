#!/usr/bin/env python3
"""Parallel refresh: AB eval + partition holdout + digest + human margin ([HYPO])."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_chronology_text_blind_v2_parallel_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(label: str, cmd: list[str]) -> dict[str, Any]:
    print(f"==> [{label}]", " ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=str(ROOT))
    return {"label": label, "exit_code": rc, "cmd": cmd}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-ab", action="store_true", help="Reuse existing v1/v2 eval artifacts")
    args = ap.parse_args()

    py = sys.executable
    steps: dict[str, dict[str, Any]] = {}

    if not args.skip_ab:
        ab = _run("ab_v1_v2", [py, str(ROOT / "scripts/run_logos_chronology_text_blind_v2_ab_v1.py")])
        steps["ab_v1_v2"] = ab
        if ab["exit_code"] != 0:
            _write_manifest(steps, ok=False)
            return 1

    wave2 = [
        (
            "holdout_partitions",
            [py, str(ROOT / "scripts/summarize_logos_chronology_partition_holdout_v1.py")],
        ),
        (
            "off_fixture_ab",
            [
                py,
                str(ROOT / "scripts/run_logos_chronology_off_fixture_text_blind_v2_ab_v1.py"),
                "--include-no-hints",
            ],
        ),
        (
            "human_margin",
            [py, str(ROOT / "scripts/build_logos_hardset_era_human_margin_report_v1.py")],
        ),
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_run, label, cmd): label for label, cmd in wave2}
        for fut in as_completed(futures):
            label = futures[fut]
            steps[label] = fut.result()

    if any(steps[k]["exit_code"] != 0 for k in ("holdout_partitions", "off_fixture_ab", "human_margin")):
        _write_manifest(steps, ok=False)
        return 1

    digest = _run(
        "digest",
        [py, str(ROOT / "scripts/build_logos_chronology_era_eval_digest_v1.py")],
    )
    steps["digest"] = digest

    ok = digest["exit_code"] == 0
    _write_manifest(steps, ok=ok)
    return 0 if ok else 1


def _write_manifest(steps: dict[str, dict[str, Any]], *, ok: bool) -> None:
    doc = {
        "schema": "logos_chronology_text_blind_v2_parallel_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "steps": steps,
        "outputs": [
            "reports/logos_chronology_text_blind_v2_ab_v1_latest.json",
            "reports/logos_chronology_text_blind_v2_holdout_v1_latest.json",
            "reports/logos_chronology_off_fixture_text_blind_v2_ab_v1_latest.json",
            "reports/logos_chronology_off_fixture_holdout_v1_latest.json",
            "reports/logos_chronology_era_blind_eval_digest_v1_latest.md",
            "reports/logos_hardset_era_human_margin_report_v1_latest.json",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(json.dumps({"ok": ok}, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
