#!/usr/bin/env python3
"""Bootstrap WTT pilot tenant corpus copy + intake manifest ([HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_lines(path: Path) -> list[str]:
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def bootstrap(
    *,
    tenant_id: str,
    source_jsonl: Path,
    max_sessions: int,
    customer_masked: bool,
    stub_template: bool,
    operator_panel: bool,
    validate_report: Path | None,
    fsm_batch_report: Path | None,
) -> dict[str, Any]:
    lines = _load_lines(source_jsonl)[:max_sessions]
    out_dir = ROOT / "data/wtt/intake"
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_out = out_dir / f"wtt_pilot_{tenant_id}_v1.jsonl"

    rows: list[str] = []
    for i, line in enumerate(lines):
        obj: dict[str, Any] = json.loads(line)
        labels = list(obj.get("labels") or [])
        if stub_template:
            if "synthetic_stub" not in labels:
                raise ValueError(
                    f"stub_template intake requires synthetic_stub label session_id={obj.get('session_id')}"
                )
            if "synthetic_spicy" in labels or obj.get("synthetic_spicy"):
                raise ValueError(
                    f"stub_template rejects synthetic_spicy session_id={obj.get('session_id')}"
                )
            obj["customer_provided"] = False
            if "pilot_template" not in labels:
                labels.append("pilot_template")
        elif operator_panel:
            if "operator_panel" not in labels or "internal_dogfood" not in labels:
                raise ValueError(
                    f"operator_panel intake requires operator_panel+internal_dogfood "
                    f"session_id={obj.get('session_id')}"
                )
            if "synthetic_spicy" in labels or obj.get("synthetic_spicy"):
                raise ValueError(
                    f"operator_panel rejects synthetic_spicy session_id={obj.get('session_id')}"
                )
            obj["customer_provided"] = False
            if "operator_panel_intake" not in labels:
                labels.append("operator_panel_intake")
        elif customer_masked:
            if "synthetic_spicy" in labels or obj.get("synthetic_spicy"):
                raise ValueError(
                    f"customer_masked intake rejects synthetic_spicy row session_id={obj.get('session_id')}"
                )
            if "synthetic_stub" in labels:
                raise ValueError(
                    f"customer_masked intake rejects synthetic_stub row session_id={obj.get('session_id')}"
                )
            if "operator_panel" in labels:
                raise ValueError(
                    f"customer_masked intake rejects operator_panel row session_id={obj.get('session_id')}"
                )
            obj["customer_provided"] = True
            if "customer_pilot_intake" not in labels:
                labels.append("customer_pilot_intake")
        else:
            obj["customer_provided"] = bool(obj.get("customer_provided", False))
        obj["tenant_id"] = tenant_id
        obj["pilot_intake"] = True
        obj["send_gate"] = "HOLD"
        obj["ready_for_external_send"] = False
        obj["labels"] = labels
        obj["source"] = f"wtt_pilot_intake_from_{source_jsonl.stem}"
        rows.append(json.dumps(obj, ensure_ascii=False))

    corpus_out.write_text("\n".join(rows) + "\n", encoding="utf-8")

    if stub_template:
        provenance = "customer_masked_stub_template_rehearsal_v1"
        status = "active_stub_template_rehearsal"
    elif operator_panel:
        provenance = "operator_panel_internal_dogfood_v1"
        status = "active_operator_panel_intake"
    elif customer_masked:
        provenance = "customer_masked_jsonl_v1"
        status = "active_customer_pilot_intake"
    else:
        provenance = "synthetic_or_dev_jsonl_v1"
        status = "active_synthetic_dev_intake"
    manifest: dict[str, Any] = {
        "schema": "wtt_pilot_intake_manifest_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "tenant_id": tenant_id,
        "status": status,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "corpus_path": _rel_to_root(corpus_out),
        "corpus_session_count": len(rows),
        "corpus_provenance": provenance,
        "source_jsonl": _rel_to_root(source_jsonl),
        "labels": ["DRAFT", "research_only", "wtt_pilot_intake", "publish_allowed=false"],
        "boundary_ack": (
            "WTT session pilot — FSM/EPB observation only; not clinical gating; "
            "SEND HOLD; compression ROI chain not merged."
        ),
        "kit_ref": "docs/final/artifacts/wtt_pilot_target_intake_kit_v1_latest.json",
    }
    if validate_report and validate_report.is_file():
        manifest["validate_report"] = _rel_to_root(validate_report)
    if fsm_batch_report and fsm_batch_report.is_file():
        manifest["fsm_batch_report"] = _rel_to_root(fsm_batch_report)

    manifest_path = ROOT / f"reports/wtt_pilot_intake_{tenant_id}_v1.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_path"] = _rel_to_root(manifest_path)
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--source-jsonl", type=Path, required=True)
    ap.add_argument("--max-sessions", type=int, default=30)
    ap.add_argument("--customer-masked", action="store_true")
    ap.add_argument("--stub-template", action="store_true")
    ap.add_argument("--operator-panel", action="store_true")
    ap.add_argument("--validate-report", type=Path, default=None)
    ap.add_argument("--fsm-batch-report", type=Path, default=None)
    args = ap.parse_args()

    src = args.source_jsonl.resolve()
    if not src.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {src}"}))
        return 1

    try:
        flags = sum([args.customer_masked, args.stub_template, args.operator_panel])
        if flags > 1:
            print(json.dumps({"ok": False, "error": "use only one intake lane flag"}))
            return 1
        manifest = bootstrap(
            tenant_id=args.tenant_id,
            source_jsonl=src,
            max_sessions=args.max_sessions,
            customer_masked=args.customer_masked,
            stub_template=args.stub_template,
            operator_panel=args.operator_panel,
            validate_report=args.validate_report.resolve() if args.validate_report else None,
            fsm_batch_report=args.fsm_batch_report.resolve() if args.fsm_batch_report else None,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    print(json.dumps({"ok": True, "tenant_id": args.tenant_id, "sessions": manifest["corpus_session_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
