# Keywords: lg factcheck, shard jaccard

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_lg_hs_before_after_factcheck_v1.py"
OUT = ROOT / "docs/final/artifacts/lg_hs_before_after_factcheck_v1_latest.json"


def test_build_factcheck_has_corrected_claims() -> None:
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "lg_hs_before_after_factcheck_v1"
    claims = doc.get("claims") or {}
    assert claims["shadow_auditor_17_of_17"]["verdict"] == "FAIL_DO_NOT_USE"
    assert claims["domain_table_per_shard_saving"]["verdict"] == "FAIL_DO_NOT_USE"
    shards = doc.get("frozen_bench_shard_jaccard") or []
    scm = next(x for x in shards if x["shard_id"] == "zone_a_scm")
    assert scm["avg_jaccard"] > 0.8
    assert scm["min_jaccard"] == 0.6666666666666666
