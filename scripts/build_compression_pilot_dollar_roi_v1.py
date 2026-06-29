#!/usr/bin/env python3
"""Build customer dollar/KRW ROI receipt from PoC + metering (real customer only by default)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROI = ROOT / "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_rehearsal(intake_path: Path | None, tenant_id: str) -> bool:
    if intake_path and intake_path.is_file():
        doc = _load(intake_path)
        labels = doc.get("labels") or []
        if "rehearsal_not_customer" in labels:
            return True
        if doc.get("status") == "active_rehearsal":
            return True
    return tenant_id.startswith("prospect-rehearsal")


def build_roi(
    *,
    tenant_id: str,
    poc: dict[str, Any],
    metering: dict[str, Any] | None,
    input_usd_per_1m: float,
    output_usd_per_1m: float,
    krw_per_usd: float,
    monthly_volume_multiplier: float,
    allow_illustrative_rehearsal: bool,
    intake_path: Path | None,
) -> dict[str, Any] | None:
    if _is_rehearsal(intake_path, tenant_id) and not allow_illustrative_rehearsal:
        return None

    cases = poc.get("cases") or []
    total_in = sum(int(c.get("token_in_proxy") or 0) for c in cases if c.get("ok"))
    if total_in <= 0:
        agg = poc.get("aggregate") or {}
        mean_save = float(agg.get("mean_token_saving_rate_proxy") or 0.0)
        case_count = int(poc.get("case_count") or 1)
        total_in = 400 * case_count
        tokens_saved = int(round(total_in * mean_save))
    else:
        tokens_saved = sum(
            int(c.get("token_in_proxy") or 0) - int(c.get("token_out_proxy") or 0)
            for c in cases
            if c.get("ok")
        )

    monthly_in = int(round(total_in * monthly_volume_multiplier))
    monthly_saved = int(round(tokens_saved * monthly_volume_multiplier))
    input_usd_per_token = input_usd_per_1m / 1_000_000.0
    monthly_usd = round(monthly_saved * max(input_usd_per_token, 0.0), 2)
    monthly_krw = int(round(monthly_usd * krw_per_usd))

    meter_note = None
    if metering:
        magg = (metering.get("metering") or {}).get("aggregate") or {}
        meter_note = {
            "global_saving_rate": magg.get("global_saving_rate"),
            "events_in_band_40_50": magg.get("events_in_band_40_50"),
        }

    status = "illustrative_rehearsal" if _is_rehearsal(intake_path, tenant_id) else "customer_measured"
    return {
        "status": status,
        "assumptions": {
            "input_usd_per_1m_tokens": input_usd_per_1m,
            "output_usd_per_1m_tokens": output_usd_per_1m,
            "krw_per_usd": krw_per_usd,
            "monthly_volume_multiplier": monthly_volume_multiplier,
            "metering_cross_check": meter_note,
        },
        "monthly_tokens_in_proxy": monthly_in,
        "monthly_tokens_saved_proxy": monthly_saved,
        "monthly_savings_usd": monthly_usd,
        "monthly_savings_krw": monthly_krw,
        "boundary_ack": "Token proxy + list prices — not a billing commitment; counsel + contract clauses required.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--poc-json", type=Path, required=True)
    ap.add_argument("--metering-appendix-json", type=Path)
    ap.add_argument("--intake-json", type=Path)
    ap.add_argument("--roi-report-json", type=Path, default=DEFAULT_ROI)
    ap.add_argument("--input-usd-per-1m", type=float, default=2.5)
    ap.add_argument("--output-usd-per-1m", type=float, default=10.0)
    ap.add_argument("--krw-per-usd", type=float, default=1350.0)
    ap.add_argument("--monthly-volume-multiplier", type=float, default=1000.0)
    ap.add_argument(
        "--allow-illustrative-rehearsal",
        action="store_true",
        help="Compute illustrative ROI for rehearsal tenants (not for external send).",
    )
    args = ap.parse_args()

    poc_path = args.poc_json.resolve()
    if not poc_path.is_file():
        print(f"error: missing poc: {poc_path}", file=sys.stderr)
        return 2

    intake = args.intake_json
    if intake is None:
        guess = ROOT / f"reports/compression_b2b_prospect_poc_corpus_{args.tenant_id}_v1.json"
        intake = guess if guess.is_file() else None

    metering_doc = None
    if args.metering_appendix_json and args.metering_appendix_json.is_file():
        metering_doc = _load(args.metering_appendix_json.resolve())

    roi_block = build_roi(
        tenant_id=args.tenant_id,
        poc=_load(poc_path),
        metering=metering_doc,
        input_usd_per_1m=args.input_usd_per_1m,
        output_usd_per_1m=args.output_usd_per_1m,
        krw_per_usd=args.krw_per_usd,
        monthly_volume_multiplier=args.monthly_volume_multiplier,
        allow_illustrative_rehearsal=args.allow_illustrative_rehearsal,
        intake_path=intake.resolve() if intake else None,
    )

    roi_path = args.roi_report_json.resolve()
    roi_doc = _load(roi_path) if roi_path.is_file() else {
        "schema": "compression_b2b_pilot_roi_report_v1",
        "tenant_id": args.tenant_id,
    }
    roi_doc["generated_at_utc"] = _utc()
    roi_doc["tenant_id"] = args.tenant_id
    if roi_block is None:
        roi_doc["customer_dollar_roi"] = None
        roi_doc["customer_krw_roi"] = None
        roi_doc["roi_status"] = "pending_customer_corpus"
    else:
        roi_doc["customer_dollar_roi"] = roi_block
        roi_doc["customer_krw_roi"] = {
            "monthly_savings_krw": roi_block["monthly_savings_krw"],
            "status": roi_block["status"],
        }
        roi_doc["roi_status"] = roi_block["status"]

    roi_path.parent.mkdir(parents=True, exist_ok=True)
    roi_path.write_text(json.dumps(roi_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "roi_status": roi_doc.get("roi_status"),
                "output": str(roi_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
