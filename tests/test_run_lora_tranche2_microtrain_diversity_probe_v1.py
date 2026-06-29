from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_lora_tranche2_microtrain_diversity_probe_v1_dry_run() -> None:
    out = ROOT / "reports" / "tmp_lora_microtrain_diversity_dry_run_test.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_lora_tranche2_microtrain_diversity_probe_v1.py"),
            "--dry-run",
            "--pack-count",
            "2",
            "--rows-per-pack-cap",
            "4",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lora_tranche2_microtrain_diversity_probe_v1"
    assert doc["dry_run"] is True
    assert len(doc["packs"]) == 2
