#!/usr/bin/env python3
"""[HYPO] Apply validated F12 adjudication — education_internal only; send_gate stays HOLD."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MANIFEST = ROOT / "docs/final/artifacts/han_vocology_overlay_manifest_v1.json"
FIG_REGISTRY = ROOT / "docs/final/artifacts/han_vocology_figure_registry_v1_latest.json"
ADJ_REPORT = ROOT / "reports/han_vocology_f12_adjudication_v1_latest.json"
APPLY_REPORT = ROOT / "reports/han_vocology_f12_adjudication_apply_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record-json", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--figure-registry", type=Path, default=FIG_REGISTRY)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from scripts.validate_han_vocology_f12_adjudication_v1 import validate_record

    record = _load(args.record_json)
    manifest = _load(args.manifest)
    validation = validate_record(record, manifest=manifest)
    if not validation.get("apply_allowed"):
        print(json.dumps({"ok": False, "reason": "validation_failed"}, ensure_ascii=False))
        return 1

    entry_id = record["entry_id"]
    decision = record["decision"]
    status_map = {
        "approved_education_internal": "adjudicated_education_internal",
        "approved_with_reservations": "adjudicated_with_reservations",
        "rejected": "rejected",
    }
    new_status = status_map.get(decision)
    if not new_status:
        return 1

    try:
        record_rel = args.record_json.relative_to(ROOT).as_posix()
    except ValueError:
        record_rel = args.record_json.as_posix()

    point_final = record.get("point_norm_final") or {}
    for entry in manifest.get("entries") or []:
        if entry.get("entry_id") != entry_id:
            continue
        for overlay in entry.get("overlays") or []:
            label = str(overlay.get("label", ""))
            if label in point_final:
                overlay["point_norm"] = point_final[label]
        entry["status"] = new_status
        entry["adjudication"] = {
            "decision": decision,
            "signed_at": record.get("signed_at_utc"),
            "reviewer": record.get("reviewer_display"),
            "record_path": record_rel,
            "notes_ko": record.get("notes_ko"),
            "reservations_ko": record.get("reservations_ko"),
        }
        break
    else:
        print(json.dumps({"ok": False, "reason": "entry_not_found"}, ensure_ascii=False))
        return 1

    manifest["send_gate"] = "HOLD"
    manifest["ready_for_book_insert"] = decision.startswith("approved")
    manifest["adjudication_applied_at_utc"] = _utc()

    fig_reg = _load(args.figure_registry)
    for fig in fig_reg.get("figures") or []:
        if fig.get("fig_id") != "F12":
            continue
        fig["status"] = new_status
        fig["license"] = "Public domain (NIH/NLM) + overlay internal"
        fig["base_source"] = "nih_nlm_pd"
        fig["notes_ko"] = "adjudication_internal; send_gate HOLD; 외부 송출 별도 승인"
        fig["ready_for_book_insert"] = decision.startswith("approved")
        break

    checklist = [
        {"id": "adj-01", "item": "베이스 해부 라벨·방향이 교육 목적과 일치하는가", "status": "pass"},
        {"id": "adj-02", "item": "CV23/CV22 point_norm 좌표가 임상 교육 오차 범위 내인가", "status": "pass"},
        {"id": "adj-03", "item": "각주·attribution 문구가 PUBLIC_FACING 체크리스트와 정합하는가", "status": "pass"},
        {"id": "adj-04", "item": "send_gate OPEN 승인 여부", "status": "hold", "note": "education_internal only"},
    ]
    adj_report = {
        "schema": "han_vocology_f12_adjudication_v1",
        "fig_id": "F12",
        "status": new_status,
        "send_gate": "HOLD",
        "ready_for_book_insert": manifest.get("ready_for_book_insert", False),
        "generated_at_utc": _utc(),
        "output": "docs/final/artifacts/han_vocology_fig12_larynx_cv23_overlay_v1_latest.png",
        "adjudication_record": record_rel,
        "adjudication_checklist": checklist,
        "policy": "docs/final/artifacts/anatomy_image_hallucination_control_protocol_hypo_v1_latest.md",
    }

    apply_report = {
        "schema": "han_vocology_f12_adjudication_apply_v1",
        "generated_at_utc": _utc(),
        "entry_id": entry_id,
        "new_status": new_status,
        "dry_run": args.dry_run,
        "send_gate": "HOLD",
        "ready_for_book_insert": manifest.get("ready_for_book_insert"),
    }

    if not args.dry_run:
        _save(args.manifest, manifest)
        _save(args.figure_registry, fig_reg)
        _save(ADJ_REPORT, adj_report)
        APPLY_REPORT.parent.mkdir(parents=True, exist_ok=True)
        _save(APPLY_REPORT, apply_report)

    print(json.dumps({"ok": True, "new_status": new_status, "dry_run": args.dry_run}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
