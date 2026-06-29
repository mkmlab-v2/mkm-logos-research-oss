#!/usr/bin/env python3
"""Phase 0+1 corpus expansion setup — pilot + sidecar container + HG queue wave 1.

Does NOT merge into logos_cosmic_anchor_batch_v1.

Reproducible:
  py scripts/run_logos_corpus_expansion_setup_v1.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "data/logos/sidecar_apocrypha_dss_hypo_v1.jsonl"
SIDECAR_README = ROOT / "data/logos/sidecar_apocrypha_dss_hypo_v1.README.md"


def ensure_sidecar() -> None:
    SIDECAR.parent.mkdir(parents=True, exist_ok=True)
    if not SIDECAR.is_file():
        SIDECAR.write_text("", encoding="utf-8")
    if not SIDECAR_README.is_file():
        SIDECAR_README.write_text(
            "# Tier 2/3 Logos sidecar (HYPO)\n\n"
            "- Format: JSONL, schema `logos_sidecar_apocrypha_dss_hypo_v1`\n"
            "- Tier 2: apocrypha · Tier 3: DSS (1QS, 4Q258, …)\n"
            "- **Never** merge into `logos_cosmic_anchor_batch_v1` without human gate\n"
            "- SSOT guide: `docs/final/LOGOS_NOTEBOOK_META_GUIDE.md`\n",
            encoding="utf-8",
        )


def main() -> int:
    ensure_sidecar()
    steps = (
        ["scripts/run_logos_corpus_expansion_pilot_v1.py"],
        ["scripts/build_logos_corpus_expansion_human_gate_queue_v1.py", "--wave", "1"],
    )
    for parts in steps:
        proc = subprocess.run([sys.executable, *parts], cwd=ROOT, check=False)
        if proc.returncode != 0:
            print(f"FAIL: {' '.join(parts)} exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
        print(f"OK: {parts[0]}")
    print(f"SIDECAR: {SIDECAR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
