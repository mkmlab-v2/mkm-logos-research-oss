#!/usr/bin/env python3
"""Build compression B2B pilot metering + SLA appendix JSON from metering log."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA_PATH = ROOT / "docs/final/schemas/compression_b2b_pilot_metering_appendix_v1.schema.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/compression_b2b_pilot_metering_appendix_latest.json"
ACTIVE_REPORT = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
KPI_GATE = ROOT / "docs/final/artifacts/general_compression_kpi_gate_v2.json"
DEFAULT_LOG = ROOT / "reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl"

DISCLAIMERS = [
    "Reference bench and AB gate figures describe MKM frozen internal corpora; they do not replace tenant workload measurement.",
    "Jaccard is a lexical reconstruction proxy, not a guarantee against semantic drift or hallucination.",
    "This appendix supports B2B token-economy engineering observation only; not investment, medical, or trade execution advice.",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_log(root: Path, override: Path | None) -> Path:
    if override is not None:
        return override.resolve()
    raw = os.environ.get("TRACK_A_METERING_LOG_PATH", "").strip()
    if raw:
        return Path(raw).resolve()
    return (root / DEFAULT_LOG).resolve()


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _load_meter_rows(log_path: Path) -> tuple[list[dict[str, Any]], int]:
    if not log_path.is_file():
        return [], 0
    rows: list[dict[str, Any]] = []
    bad = 0
    for ln in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip():
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            bad += 1
    return rows, bad


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tb = sum(int(r.get("tokens_before") or 0) for r in rows)
    ta = sum(int(r.get("tokens_after") or 0) for r in rows)
    saving = (tb - ta) / tb if tb > 0 else 0.0
    in_band = 0
    for r in rows:
        sr = r.get("saving_rate")
        if sr is not None:
            s = float(sr)
            if 0.40 <= s <= 0.50:
                in_band += 1
                continue
        if tb > 0 and r.get("tokens_before") and r.get("tokens_after"):
            b = int(r["tokens_before"])
            a = int(r["tokens_after"])
            if b > 0:
                s = (b - a) / b
                if 0.40 <= s <= 0.50:
                    in_band += 1
    n = len(rows)
    band_rate = (in_band / n) if n else None
    return {
        "tokens_before_sum": tb,
        "tokens_after_sum": ta,
        "global_saving_rate": round(saving, 6),
        "events_in_band_40_50": in_band,
        "band_hit_rate_40_50": round(band_rate, 6) if band_rate is not None else None,
    }


def _bench_jaccard_proxy() -> float | None:
    if not ACTIVE_REPORT.is_file():
        return None
    try:
        doc = json.loads(ACTIVE_REPORT.read_text(encoding="utf-8"))
        metrics = doc.get("compression_metrics") or doc.get("quality_gate") or {}
        v = metrics.get("avg_reconstruction_fidelity_jaccard")
        if v is None and isinstance(doc.get("rows"), list) and doc["rows"]:
            v = doc["rows"][0].get("reconstruction_fidelity_jaccard")
        return round(float(v), 6) if v is not None else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def seed_demo_events(log_path: Path) -> None:
    from scripts.core.billing_meter import validate_meter_event

    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    samples = [
        {"sla_track": "active", "tokens_before": 100, "tokens_after": 52, "saving_rate": 0.48, "domain": "ssot"},
        {"sla_track": "active", "tokens_before": 200, "tokens_after": 100, "saving_rate": 0.50, "domain": "scm"},
        {"sla_track": "active", "tokens_before": 120, "tokens_after": 68, "saving_rate": 0.433, "domain": "hangul"},
    ]
    for row in samples:
        event = dict(row)
        event["client_request_id"] = "pilot-demo-seed"
        event.setdefault("meter_schema", "track_a_metering_log_v1")
        event.setdefault("ts_utc", _utc())
        validate_meter_event(event)
        lines.append(json.dumps(event, ensure_ascii=False))
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_doc(
    *,
    root: Path,
    tenant_id: str,
    period_label: str,
    contract_ref: str | None,
    log_path: Path,
) -> dict[str, Any]:
    rows, parse_errors = _load_meter_rows(log_path)
    return {
        "schema": "compression_b2b_pilot_metering_appendix_v1",
        "generated_at_utc": _utc(),
        "pilot": {
            "tenant_id": tenant_id,
            "period_label": period_label,
            "contract_ref": contract_ref or "",
            "one_pager_path": "docs/final/artifacts/compression_b2b_pilot_onepager_v1.md",
        },
        "metering": {
            "meter_schema": "track_a_metering_log_v1",
            "log_path_relative": _rel(root, log_path),
            "events_total": len(rows),
            "parse_errors": parse_errors,
            "aggregate": _aggregate(rows),
            "integrity_note": (
                "Jaccard scores in contracts refer to lexical token overlap proxy only, "
                "not semantic equivalence."
            ),
            "bench_jaccard_proxy": _bench_jaccard_proxy(),
        },
        "sla_appendix": {
            "status": "draft_internal",
            "sla_draft_pointer": "docs/final/TRACK_A_SLA_DRAFT.md",
            "settlement_mode": "manual_invoice_v0",
            "hydrate_window_required": True,
            "target_saving_band_pct": {"min": 40, "max": 50},
            "obligations": [
                "Append-only metering via POST /v1/metering/log or eval_context.meter_log",
                "Weekly metering summary export for pilot review",
                "Hydrate window re-measurement before production SLA attachment",
            ],
            "exclusions": [
                "No automated live-trading or prophecy promotion triggers from bench KPI",
                "No guarantee of semantic meaning preservation from Jaccard alone",
                "Free-form NL negotiation and legal negation-critical text excluded from pilot scope",
            ],
        },
        "evidence_pointers": {
            "active_report_path": _rel(root, ACTIVE_REPORT),
            "kpi_gate_path": _rel(root, KPI_GATE),
            "metering_summary_path": "docs/final/artifacts/track_a_metering_summary_latest.json",
        },
        "disclaimers": list(DISCLAIMERS),
        "governance": {
            "publish_allowed": False,
            "pre_send_gate": "scripts/check_compression_enterprise_summary_readiness_v1.py",
            "fail_comp_note": "FAIL-COMP-004: do not auto-merge bench KPI into Track A live trading.",
        },
    }


def validate_doc(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build compression B2B pilot metering appendix v1.")
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--tenant-id", default="pilot-demo")
    ap.add_argument("--period-label", default="pilot metering window")
    ap.add_argument("--contract-ref", default="")
    ap.add_argument("--metering-log", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--seed-demo", action="store_true", help="Replace log with 3 demo metering rows")
    ap.add_argument("--allow-empty", action="store_true", help="Allow zero events (smoke only)")
    ap.add_argument("--skip-validate", action="store_true")
    args = ap.parse_args()
    root = args.workspace_root.resolve()
    log_path = _resolve_log(root, args.metering_log)

    if args.seed_demo:
        seed_demo_events(log_path)

    rows, _ = _load_meter_rows(log_path)
    if not rows and not args.allow_empty:
        print(f"error: no metering events in {log_path}; use --seed-demo or --allow-empty", file=sys.stderr)
        return 2

    doc = build_doc(
        root=root,
        tenant_id=str(args.tenant_id),
        period_label=str(args.period_label),
        contract_ref=str(args.contract_ref).strip() or None,
        log_path=log_path,
    )
    if not args.skip_validate:
        validate_doc(doc, SCHEMA_PATH)

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
