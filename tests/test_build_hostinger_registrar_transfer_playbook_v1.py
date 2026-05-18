"""Playbook builder smoke from fixture readiness JSON."""
from __future__ import annotations

import json
from pathlib import Path

import scripts.build_hostinger_registrar_transfer_playbook_v1 as mod

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = {
    "target_registrar": "Cloudflare Registrar",
    "domains": [
        {
            "apex": "jema-ai.com",
            "ns_includes_cloudflare": True,
            "cf_active_zone_found": True,
            "delegation_evidence_ok": True,
            "transfer_completed": False,
            "transfer_ready_guess": False,
        },
        {
            "apex": "personadiary.com",
            "ns_includes_cloudflare": False,
            "cf_active_zone_found": False,
            "delegation_evidence_ok": False,
            "transfer_completed": False,
            "transfer_ready_guess": False,
        },
    ],
}


def test_playbook_waves(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.json"
    out = tmp_path / "playbook.json"
    readiness.write_text(json.dumps(FIXTURE), encoding="utf-8")
    assert mod.main.__module__
    import sys

    old = sys.argv
    try:
        sys.argv = ["", str(readiness), str(out)]
        assert mod.main() == 0
    finally:
        sys.argv = old
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "hostinger_registrar_transfer_playbook_v1"
    waves = payload["recommended_sequence"]
    assert waves[0]["wave"] == 1
    assert waves[0]["domains"][0]["apex"] == "jema-ai.com"
    assert any(w["wave"] == 3 for w in waves)
