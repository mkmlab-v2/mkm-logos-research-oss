"""jema-ai hub JEMA OS brand handoff builder smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_jema_ai_hub_brand_handoff_v1.py"


def test_build_hub_handoff_schema_and_ctas():
    out = ROOT / "reports/_test_jema_ai_hub_brand_handoff_v1.json"
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert out.is_file()

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "jema_ai_hub_brand_handoff_v1"
    assert doc["surface"]["path"] == "/hub"
    assert doc["surface"]["hub_llm_enabled"] is False
    assert doc["surface"]["metering_enabled"] is False
    assert doc["governance"]["send_gate"] == "HOLD"
    assert doc["brand"]["public_os_display"] == "JEMA OS v2"
    assert doc["brand"]["internal_kernel"] == "MKM"
    assert len(doc["cta_links"]) >= 3
    keys = {row["key"] for row in doc["cta_links"]}
    assert "showroom_jemaai" in keys
    assert "premium_mkmlife" in keys
    assert "research_logos" in keys
    assert "jema_os_enterprise" in keys
    enterprise = next(r for r in doc["cta_links"] if r["key"] == "jema_os_enterprise")
    assert enterprise["href"] == "/enterprise"
    premium = next(r for r in doc["cta_links"] if r["key"] == "premium_mkmlife")
    assert "oracle-sphere" in premium["href"]
    assert doc["pointers"]["coordinate_envelope_skim"]

    out.unlink(missing_ok=True)
