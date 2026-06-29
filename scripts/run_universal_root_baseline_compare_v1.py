#!/usr/bin/env python3
"""Entry: Phase 1A baseline vs dual-plane compare (delegates to build + alias artifact)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
BUILDER = ROOT / "scripts/build_universal_root_phase1a_baseline_compare_v1.py"
CANONICAL = ROOT / "reports/universal_root_phase1a_baseline_compare_v1_latest.json"
ALIAS = ROOT / "reports/baseline_vs_dual_plane_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-crosswalk-build", action="store_true")
    args, unknown = ap.parse_known_args()

    cmd = [PY, str(BUILDER)]
    if args.skip_crosswalk_build:
        cmd.append("--skip-crosswalk-build")
    cmd.extend(unknown)

    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(proc.stdout or proc.stderr or json.dumps({"ok": False, "error": "builder_failed"}))
        return proc.returncode

    if not CANONICAL.is_file():
        print(json.dumps({"ok": False, "error": "canonical_artifact_missing"}))
        return 2

    doc = json.loads(CANONICAL.read_text(encoding="utf-8-sig"))
    doc["alias_of"] = str(CANONICAL.relative_to(ROOT)).replace("\\", "/")
    doc["entrypoint"] = "scripts/run_universal_root_baseline_compare_v1.py"
    ALIAS.parent.mkdir(parents=True, exist_ok=True)
    ALIAS.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "canonical": str(CANONICAL),
                "alias": str(ALIAS),
                "reproduce": "py scripts/run_universal_root_baseline_compare_v1.py",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
