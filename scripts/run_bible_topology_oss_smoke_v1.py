#!/usr/bin/env python3
"""Bible topology crosswalk OSS smoke — validate Tier A seed + optional rebuild check [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_SEED = ROOT / "tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json"
DEFAULT_OUT = ROOT / "reports/bible_topology_oss_smoke_v1_latest.json"
VALIDATE = ROOT / "scripts/validate_bible_topology_contrib_shard_v1.py"
BUILD = ROOT / "scripts/build_bible_topology_synoptic_passion_seed_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed-json", type=Path, default=DEFAULT_SEED)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-rebuild-check", action="store_true")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    seed = args.seed_json.resolve()
    steps: list[dict[str, Any]] = []

    proc = subprocess.run(
        [
            PY,
            str(VALIDATE.relative_to(ROOT)),
            "--json",
            str(seed.relative_to(ROOT)),
            "--min-edges",
            "3",
            "--max-edges",
            "500",
            "--stdout-only",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    validate_doc: dict[str, Any] = {}
    if proc.stdout.strip():
        try:
            validate_doc = json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            validate_doc = {"parse_error": True}
    steps.append(
        {
            "name": "validate_tier_a_seed",
            "exit_code": proc.returncode,
            "ok": proc.returncode == 0 and validate_doc.get("validation_ok") is True,
            "edge_count": validate_doc.get("edge_count"),
            "slice_id": validate_doc.get("slice_id"),
        }
    )

    rebuild_ok = True
    if not args.skip_rebuild_check and BUILD.is_file():
        proc_b = subprocess.run([PY, str(BUILD.relative_to(ROOT))], cwd=str(ROOT), capture_output=True, text=True, check=False)
        rebuild_ok = proc_b.returncode == 0
        steps.append({"name": "rebuild_seed", "exit_code": proc_b.returncode, "ok": rebuild_ok})

    ok = all(s.get("ok") for s in steps if "ok" in s)
    report: dict[str, Any] = {
        "schema": "bible_topology_oss_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "seed_json": _rel(seed),
        "parent_engine": "https://github.com/mkmlab-v2/mkm-universal-root",
        "ok": ok,
        "steps": steps,
        "telemetry": False,
        "reproduce": "py scripts/run_bible_topology_oss_smoke_v1.py",
    }

    if not args.stdout_only:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": ok, "steps": [s["name"] for s in steps]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
