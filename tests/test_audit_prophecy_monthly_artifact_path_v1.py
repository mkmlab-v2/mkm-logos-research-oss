import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_prophecy_monthly_artifact_path_v1.py"


def test_audit_exits_0_when_canonical_exists(tmp_path: Path) -> None:
    wr = tmp_path / "w"
    wr.mkdir()
    art = wr / "docs" / "final" / "artifacts"
    art.mkdir(parents=True)
    canon = art / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
    canon.write_text(
        json.dumps(
            {
                "schema": "prophecy_2026_monthly_kospi_btc_fact_safe_v1",
                "meta": {
                    "generated_at_utc": "2026-01-01T00:00:00Z",
                    "high_reliability_decision": "PASS",
                    "price_output_locked": False,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--workspace-root", str(wr)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout.strip())
    assert payload["canonical"]["exists"] is True


def test_audit_exits_1_when_canonical_missing(tmp_path: Path) -> None:
    wr = tmp_path / "empty"
    wr.mkdir()
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--workspace-root", str(wr)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
