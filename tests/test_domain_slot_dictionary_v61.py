from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_domain_slot_dictionary_v61_generates() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "curate_domain_slot_dictionary_v61.py"
    out = root / "docs" / "final" / "artifacts" / "MULTILENS_DOMAIN_SLOT_DICTIONARY_V61.json"
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "multilens_domain_slot_dictionary_v61"
    assert isinstance(doc.get("slots"), dict)
    assert "S1" in doc["slots"]
