#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append de-identified Paste Chart encounter row to local ledger [HYPO][research_only].

SSOT: data/clinic/paste_chart_encounter_ledger_v1.jsonl
Does NOT promote Track A or auto-diagnose.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "data/clinic/paste_chart_encounter_ledger_v1.jsonl"
OUT_REPORT = ROOT / "reports/clinician_paste_chart_encounter_ledger_append_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _redact_display(label: str) -> str:
    t = label.strip()
    if not t:
        return "redacted"
    if len(t) <= 1:
        return "*"
    return t[0] + "*" * min(3, len(t) - 1)


def _pipeline_summary(envelope: dict[str, Any]) -> dict[str, Any]:
    pipeline = envelope.get("pipeline") if isinstance(envelope.get("pipeline"), list) else []
    ok = sum(1 for s in pipeline if isinstance(s, dict) and s.get("status") == "ok")
    fail = sum(1 for s in pipeline if isinstance(s, dict) and s.get("status") == "fail")
    output = envelope.get("output") if isinstance(envelope.get("output"), dict) else {}
    extract = envelope.get("extract") if isinstance(envelope.get("extract"), dict) else {}
    conf = extract.get("confidence")
    return {
        "stages_ok": ok,
        "stages_fail": fail,
        "fusion_synced": bool(output.get("fusion_synced")),
        "extract_confidence": conf if conf in ("low", "high") else "low",
        "advice_warning": output.get("advice_warning"),
    }


def build_ledger_row(
    *,
    slug_or_ephemeral: str,
    display_label: str = "",
    request_id: str | None = None,
    ephemeral: bool = False,
    envelope: dict[str, Any] | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    enc_ref: dict[str, Any] = {
        "slug_or_ephemeral": slug_or_ephemeral.strip() or "ephemeral_unknown",
        "display_label_redacted": _redact_display(display_label),
        "ephemeral": ephemeral,
    }
    if request_id:
        enc_ref["request_id"] = request_id
    summary = _pipeline_summary(envelope or {})
    return {
        "schema": "clinician_paste_chart_encounter_ledger_v1",
        "ts_utc": _utc(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autobind_forbidden": True,
        "encounter_ref": enc_ref,
        "pipeline_summary": summary,
        "human_gold_required": True,
        "source": source,
    }


def append_row(ledger_path: Path, row: dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def row_from_paste_chart_response(payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    slug = str(payload.get("slug") or "ephemeral_" + _utc()[:10].replace("-", ""))
    if payload.get("ephemeral") and not str(payload.get("slug") or "").startswith("ephemeral_"):
        slug = f"ephemeral_{re.sub(r'[^a-z0-9_]+', '_', slug.lower())[:48]}"
    envelope = payload.get("session_envelope") if isinstance(payload.get("session_envelope"), dict) else None
    bundle = payload.get("patient_care_bundle") if isinstance(payload.get("patient_care_bundle"), dict) else {}
    request_id = str(bundle.get("request_id") or payload.get("request_id") or "")
    row = build_ledger_row(
        slug_or_ephemeral=slug,
        display_label=str(payload.get("display_label") or ""),
        request_id=request_id or None,
        ephemeral=bool(payload.get("ephemeral")),
        envelope=envelope,
        source=source,
    )
    audit = payload.get("eight_channel_audit_v1")
    if isinstance(audit, dict) and audit.get("schema"):
        row["eight_channel_audit_v1"] = audit
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    ap.add_argument("--from-json", type=Path, default=None, help="paste-chart API response or envelope export")
    ap.add_argument("--slug", default="")
    ap.add_argument("--display", default="")
    ap.add_argument("--request-id", default="")
    ap.add_argument("--ephemeral", action="store_true")
    ap.add_argument("--source", default="cli")
    ap.add_argument("--output", type=Path, default=OUT_REPORT)
    ns = ap.parse_args()

    if ns.from_json:
        payload = _load_json(ns.from_json)
        row = row_from_paste_chart_response(payload, source=ns.source)
    else:
        if not ns.slug.strip() and not ns.ephemeral:
            print("slug or --ephemeral required without --from-json", file=sys.stderr)
            return 2
        row = build_ledger_row(
            slug_or_ephemeral=ns.slug.strip() or f"ephemeral_{_utc()[:10]}",
            display_label=ns.display,
            request_id=ns.request_id or None,
            ephemeral=ns.ephemeral,
            source=ns.source,
        )

    append_row(ns.ledger, row)
    try:
        ledger_rel = str(ns.ledger.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        ledger_rel = str(ns.ledger)
    report = {
        "schema": "clinician_paste_chart_encounter_ledger_append_v1",
        "ok": True,
        "ledger": ledger_rel,
        "row": row,
        "reproduce": f'py scripts/append_clinician_paste_chart_encounter_ledger_v1.py --from-json "{ns.from_json}"'
        if ns.from_json
        else f'py scripts/append_clinician_paste_chart_encounter_ledger_v1.py --slug "{ns.slug}"',
    }
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
