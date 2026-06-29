#!/usr/bin/env python3
"""Verify sasang vs myeongni lens separation on encounter_sequence records [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_myeongni_sasang_lens_separation_v1_latest.json"


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


def check() -> dict[str, Any]:
    ledger_mod = _load_mod("scripts/encounter_sequence_ledger_v1.py")
    sidecar_mod = _load_mod("scripts/tkm_encounter_sequence_myeongni_sidecar_v1.py")

    records = sidecar_mod.latest_records_by_sequence_id(ledger_mod.iter_ledger_records(ROOT))
    violations: list[dict[str, Any]] = []
    checked = 0
    with_sidecar = 0

    for row in records:
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        seq_id = str(enc.get("sequence_id") or "")
        if not seq_id:
            continue
        sidecar = row.get("l5_myeongni_ref")
        if not isinstance(sidecar, dict):
            continue
        with_sidecar += 1
        checked += 1
        errs = sidecar_mod.validate_sasang_lens_separation(row)
        if errs:
            violations.append({"sequence_id": seq_id, "errors": errs})
        if sidecar.get("non_gating") is not True:
            violations.append({"sequence_id": seq_id, "errors": ["non_gating must be true"]})

    ok = with_sidecar >= 1 and not violations
    return {
        "schema": "tkm_myeongni_sasang_lens_separation_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "separation_ok": ok,
        "checked_sidecar_count": checked,
        "with_sidecar_count": with_sidecar,
        "violation_count": len(violations),
        "violations": violations[:20],
        "send_gate": "HOLD",
        "reproduce": "py scripts/check_tkm_myeongni_sasang_lens_separation_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = check()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("separation_ok"), "checked": doc.get("checked_sidecar_count")}))
    return 0 if doc.get("separation_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
