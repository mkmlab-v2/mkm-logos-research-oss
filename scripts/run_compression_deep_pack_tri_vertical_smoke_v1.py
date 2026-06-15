#!/usr/bin/env python3
"""One-shot compression deep pack tri-vertical smoke (B-track, research envelope only).

Rebuilds coverage + gates + tri checklists, reconciles commander signoff, runs core pytest.
SEND_GATE HOLD · no ACTIVE mutation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STEPS = [
    "run_zone_f_code_template_catalog_coverage_v1.py",
    "run_zone_h_en_business_template_catalog_coverage_v1.py",
    "run_zone_ko_premium_cs_template_catalog_coverage_v1.py",
    "build_compression_coding_deep_pack_gate_v1.py",
    "build_compression_en_business_deep_pack_gate_v1.py",
    "build_compression_ko_premium_cs_deep_pack_gate_v1.py",
    "build_compression_coding_deep_pack_signoff_checklist_v1.py",
    "build_compression_en_business_deep_pack_signoff_checklist_v1.py",
    "build_compression_ko_premium_cs_deep_pack_signoff_checklist_v1.py",
    "build_compression_deep_pack_tri_vertical_signoff_checklist_v1.py",
]

PYTESTS = [
    "tests/test_compression_coding_deep_pack_v1.py",
    "tests/test_compression_en_business_deep_pack_v1.py",
    "tests/test_compression_ko_premium_cs_deep_pack_v1.py",
    "tests/test_build_compression_deep_pack_tri_vertical_signoff_checklist_v1.py",
    "tests/test_build_compression_deep_pack_tri_vertical_post_signoff_checklist_v1.py",
    "tests/test_compression_sku_separation_v1.py",
]


def _run(script: str) -> None:
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compression deep pack tri-vertical smoke")
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()
    for step in STEPS:
        _run(step)
    from scripts.compression_deep_pack_tri_vertical_human_signoff_v1_lib import reconcile_from_tri_signoff_record

    reconcile_from_tri_signoff_record()
    _run("build_compression_deep_pack_tri_vertical_post_signoff_checklist_v1.py")
    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *[str(ROOT / p) for p in PYTESTS], "-q", "--tb=short"],
            cwd=str(ROOT),
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
    print('{"ok": true, "smoke": "compression_deep_pack_tri_vertical_v1"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
