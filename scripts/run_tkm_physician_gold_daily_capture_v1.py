#!/usr/bin/env python3
"""Daily physician_gold capture ingest (de-identified, non-dummy) [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_physician_gold_daily_capture_v1_latest.json"
INBOX = ROOT / "data/clinic/inbox"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_mod(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ref_exists(ref_token: str) -> bool:
    base = ROOT / "data/clinic"
    if not base.is_dir():
        return False
    for path in sorted(base.glob("clinic_constitution_mvp_v1*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
            if str(enc.get("ref_token") or "") == ref_token:
                return True
    return False


def _daily_variants() -> list[dict[str, Any]]:
    return [
        {"ai": "soyang", "physician": "soeum", "match": False, "code": "modality_insufficient"},
        {"ai": "taeeum", "physician": "taeeum", "match": True, "code": "none"},
        {"ai": "taeyang", "physician": "taeyang", "match": True, "code": "none"},
        {"ai": "soeum", "physician": "soyang", "match": False, "code": "ai_underconfident"},
    ]


def build_capture(*, day_key: str | None = None) -> dict[str, Any]:
    day = day_key or _today_key()
    ref = f"ENC-PHYSICIAN-GOLD-DAILY-{day}"
    seq = f"SEQ-PHYSICIAN-GOLD-DAILY-{day}"
    variant = _daily_variants()[hash(day) % len(_daily_variants())]
    return {
        "schema": "clinic_constitution_mvp_capture_v1",
        "version": "1.0.0",
        "ts_utc": _utc(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autobind_forbidden": True,
        "label_lane": "physician_gold",
        "encounter": {"ref_token": ref},
        "modalities_present": {
            "survey": True,
            "face_image": False,
            "voice_sample": False,
            "birth_profile": True,
        },
        "observation_proxies": {
            "cold_heat_lean": 0.48,
            "digestion_lean": 0.56,
            "activity_lean": 0.5,
            "moisture_lean": 0.52,
        },
        "ai_hypothesis": {
            "constitution": variant["ai"],
            "confidence": 0.58,
            "model_id": "physician_gold_daily_capture_v1",
            "rationale_short": "[HYPO] 일일 비식별 capture; 원장 판정 대조.",
        },
        "physician_constitution": {
            "label": variant["physician"],
            "recorded_by_role": "licensed_km_physician",
            "notes": f"[HYPO] daily capture {day}; non-PHI.",
        },
        "agreement": {
            "ai_physician_match": variant["match"],
            "disagreement_code": variant["code"],
        },
        "intake_ref": f"reports/tkm_physician_gold_daily_{day}.json",
        "patient_facing_copy_ack": True,
        "meta": {"research_only": True, "daily_capture": True, "capture_day": day},
        "_sequence_id": seq,
    }


def run(*, day_key: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    capture = build_capture(day_key=day_key)
    ref = capture["encounter"]["ref_token"]
    seq_id = capture.pop("_sequence_id")

    if _ref_exists(ref):
        return {
            "schema": "tkm_physician_gold_daily_capture_v1",
            "generated_at_utc": _utc(),
            "ok": True,
            "skipped": True,
            "reason": "already_present",
            "ref_token": ref,
            "sequence_id": seq_id,
        }

    INBOX.mkdir(parents=True, exist_ok=True)
    inbox_path = INBOX / f"physician_gold_daily_{capture['meta']['capture_day']}.json"
    inbox_path.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if dry_run:
        return {
            "schema": "tkm_physician_gold_daily_capture_v1",
            "generated_at_utc": _utc(),
            "ok": True,
            "dry_run": True,
            "ref_token": ref,
            "inbox_path": str(inbox_path).replace("\\", "/"),
        }

    ingest = _load_mod("ingest_physician_gold_clinic_capture_v1", "scripts/ingest_physician_gold_clinic_capture_v1.py")
    clf = _load_mod("tkm_dummy_row_classifier_v1", "scripts/tkm_dummy_row_classifier_v1.py")
    if clf.is_dummy_clinic_capture(capture):
        return {"ok": False, "reason": "classified_as_dummy", "ref_token": ref}

    ingest_mod = _load_mod(
        "ingest_clinic_capture_to_encounter_sequence_v1",
        "scripts/ingest_clinic_capture_to_encounter_sequence_v1.py",
    )
    doc = ingest_mod.ingest(capture, append_clinic_ledger=True, sequence_id=seq_id)
    return {
        "schema": "tkm_physician_gold_daily_capture_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "skipped": False,
        "ref_token": ref,
        "sequence_id": seq_id,
        "inbox_path": str(inbox_path).replace("\\", "/"),
        "ingest": doc,
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--day", default=None, help="YYYY-MM-DD (default: today UTC)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run(day_key=args.day, dry_run=args.dry_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "skipped": doc.get("skipped"), "ref_token": doc.get("ref_token")}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
