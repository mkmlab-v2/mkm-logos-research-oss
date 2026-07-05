#!/usr/bin/env python3
"""Static gate for KM Han Medicine Antigravity HTML mocks (pre-Cursor merge)."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MOCKS = ROOT / "projects/km_han_medicine_ui_ux/mocks"
OUT = ROOT / "reports/km_han_medicine_mock_pack_gates_v1_latest.json"

PACKS = {
    "PackE-NationalAsk": MOCKS / "PackE-NationalAsk/pack_e_national_ask.html",
    "PackF-Clinician": MOCKS / "PackF-Clinician/pack_f_clinician.html",
    "PackG-HubClinical": MOCKS / "PackG-HubClinical/pack_g_hub_clinical.html",
}

FORBIDDEN = (
    r"체질\s*확정",
    r"Track\s*A",
    r"live\s*trad",
    r"함억.*처방",
    r"두견.*처방",
)

REQUIRED_HINTS = {
    "PackE-NationalAsk": ("layer-badge", "provenance", "L0"),
    "PackF-Clinician": ("trust", "canon", "cite"),
    "PackG-HubClinical": ("clinical", "hub", "L0"),
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_pack(name: str, path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {"pack": name, "path": str(path.relative_to(ROOT)).replace("\\", "/"), "exists": path.is_file()}
    if not path.is_file():
        row["ok"] = False
        row["errors"] = ["missing_file"]
        return row
    text = path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    for pat in FORBIDDEN:
        if re.search(pat, text, re.I):
            errors.append(f"forbidden_pattern:{pat}")
    for hint in REQUIRED_HINTS.get(name, ()):
        if hint.lower() not in text.lower():
            errors.append(f"missing_hint:{hint}")
    row["ok"] = not errors
    row["errors"] = errors
    row["bytes"] = len(text.encode("utf-8"))
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    rows = [_check_pack(name, path) for name, path in PACKS.items()]
    doc = {
        "schema": "km_han_medicine_mock_pack_gates_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "all_ok": all(r.get("ok") for r in rows),
        "packs": rows,
        "reproduce": "py scripts/check_km_han_medicine_mock_pack_gates_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
