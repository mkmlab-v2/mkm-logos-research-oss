from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_build_logos_research_product_metrics() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_logos_research_product_metrics_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((_ROOT / "reports/logos_research_product_metrics_v1_latest.json").read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_research_product_metrics_v1"
    assert doc.get("public_domain") == "logos.jema-ai.com"
    no1k = _ROOT / "projects/no1kmedi/public/data/logos_research_product_metrics_v1.json"
    assert no1k.is_file()


def test_commercial_pack_skip_phase_o() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_logos_research_commercial_pack_v1.py"),
            "--skip-phase-o",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    manifest = _ROOT / "docs/final/artifacts/logos_research_commercial_product_v1_latest.json"
    assert manifest.is_file()
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc.get("public_domain") == "logos.jema-ai.com"
    assert "research_logos" in (doc.get("hub_integration") or {}).get("hub_link_key", "")
