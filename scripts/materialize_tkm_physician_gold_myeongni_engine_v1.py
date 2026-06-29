#!/usr/bin/env python3
"""Materialize engine myeongni reports for physician_gold captures [HYPO]."""

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
OUT = ROOT / "reports/tkm_physician_gold_myeongni_engine_materialize_v1_latest.json"


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


def _iter_captures() -> list[dict[str, Any]]:
    clf = _load_mod("scripts/tkm_dummy_row_classifier_v1.py")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(capture: dict[str, Any]) -> None:
        if capture.get("schema") != "clinic_constitution_mvp_capture_v1":
            return
        if clf.is_dummy_clinic_capture(capture):
            return
        ref = str((capture.get("encounter") or {}).get("ref_token") or "")
        if not ref or ref in seen:
            return
        mods = capture.get("modalities_present") if isinstance(capture.get("modalities_present"), dict) else {}
        if mods.get("birth_profile") is not True:
            return
        seen.add(ref)
        rows.append(capture)

    clinic = ROOT / "data/clinic"
    for path in sorted(clinic.glob("clinic_constitution_mvp_v1*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            _add(json.loads(line))

    inbox = ROOT / "data/clinic/inbox"
    if inbox.is_dir():
        for path in sorted(inbox.glob("physician_gold*.json")):
            _add(json.loads(path.read_text(encoding="utf-8-sig")))

    return rows


def run(*, dry_run: bool = False) -> dict[str, Any]:
    builder = _load_mod("scripts/build_physician_gold_myeongni_engine_report_v1.py")
    birth_mod = _load_mod("scripts/tkm_physician_gold_birth_profile_v1.py")
    captures = _iter_captures()
    built = 0
    skipped = 0
    refs: list[str] = []

    for capture in captures:
        ref = str((capture.get("encounter") or {}).get("ref_token") or "")
        rel = birth_mod.engine_report_relpath(ref)
        target = ROOT / rel
        if target.is_file() and not dry_run:
            meta = json.loads(target.read_text(encoding="utf-8-sig")).get("meta") or {}
            if meta.get("engine_built") is True:
                skipped += 1
                continue
        if dry_run:
            built += 1
            refs.append(ref)
            continue
        doc = builder.build_for_capture(capture)
        if doc.get("ok"):
            built += 1
            refs.append(ref)

    engine_on_disk = sum(
        1
        for capture in captures
        if (ROOT / birth_mod.engine_report_relpath(str((capture.get("encounter") or {}).get("ref_token") or ""))).is_file()
    )
    return {
        "schema": "tkm_physician_gold_myeongni_engine_materialize_v1",
        "generated_at_utc": _utc(),
        "ok": (built >= 1 or skipped >= 1 or engine_on_disk >= 1) and len(captures) >= 1,
        "dry_run": dry_run,
        "built_count": built,
        "skipped_count": skipped,
        "engine_on_disk_count": engine_on_disk,
        "capture_count": len(captures),
        "ref_tokens": refs,
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run(dry_run=args.dry_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "built": doc.get("built_count")}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
