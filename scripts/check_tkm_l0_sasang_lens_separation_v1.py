#!/usr/bin/env python3
"""Check L0 red-flag layer does not merge into sasang constitution headline [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports/tkm_l0_sasang_lens_separation_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_mod(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run() -> dict[str, Any]:
    l0_mod = _load_mod("scripts/tkm_encounter_sequence_l0_router_v1.py")
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    records = l0_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))

    checked = 0
    errors: list[dict[str, str]] = []
    for row in records:
        if not l0_mod.is_l0_wired(row):
            continue
        checked += 1
        for err in l0_mod.validate_l0_sasang_separation(row):
            enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
            errors.append({"sequence_id": str(enc.get("sequence_id") or ""), "error": err})

    return {
        "schema": "tkm_l0_sasang_lens_separation_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "checked": checked,
        "separation_ok": checked >= 1 and not errors,
        "errors": errors,
        "reproduce": "py scripts/check_tkm_l0_sasang_lens_separation_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("separation_ok"), "checked": doc.get("checked")}))
    return 0 if doc.get("separation_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
