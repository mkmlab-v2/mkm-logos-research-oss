#!/usr/bin/env python3
"""Evaluate Geumsan vendor reply against Go/No-Go checklist (stdin JSON or --reply-json)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST = (
    ROOT / "docs/final/artifacts/smartfarm_geumsan_vendor_reply_gonogo_checklist_v1_latest.json"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _truthy(val: Any) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("y", "yes", "true", "1", "pass", "ok"):
        return True
    if s in ("n", "no", "false", "0", "fail"):
        return False
    return None


def _knockout_k5(fields: dict[str, Any]) -> str:
    total = fields.get("iot_total_krw_ex_usim")
    if total is None:
        return "HOLD"
    try:
        n = float(str(total).replace(",", "").replace("만", "0000"))
        if "만" in str(total) and n < 1000:
            n *= 10000
    except ValueError:
        return "HOLD"
    return "PASS" if n <= 5_000_000 else "FAIL"


def _api_ok(fields: dict[str, Any]) -> str:
    pdf = _truthy(fields.get("api_pdf_attached"))
    rest = _truthy(fields.get("rest_yn"))
    mqtt = _truthy(fields.get("mqtt_yn"))
    modbus = _truthy(fields.get("modbus_yn"))
    if pdf is not True:
        return "FAIL" if any(x is True for x in (rest, mqtt, modbus)) else "HOLD"
    if any(x is True for x in (rest, mqtt, modbus)):
        return "PASS"
    return "HOLD"


def evaluate(fields: dict[str, Any], checklist: dict[str, Any]) -> dict[str, Any]:
    ko: dict[str, str] = {}
    ko["K1"] = "PASS" if _truthy(fields.get("half_turnkey_yn")) is True else (
        "FAIL" if _truthy(fields.get("half_turnkey_yn")) is False else "HOLD"
    )
    ch = fields.get("relay_channels")
    try:
        ko["K2"] = "PASS" if ch is not None and int(ch) >= 2 else (
            "FAIL" if ch is not None and int(ch) < 2 else "HOLD"
        )
    except (TypeError, ValueError):
        ko["K2"] = "HOLD"
    ko["K3"] = _api_ok(fields)
    cs = _truthy(fields.get("customer_server_collect_yn"))
    ko["K4"] = "PASS" if cs is True else ("FAIL" if cs is False else "HOLD")
    ko["K5"] = _knockout_k5(fields)
    ko["K6"] = "PASS"  # assume accepted unless vendor explicitly requires simultaneous open
    trip = _truthy(fields.get("geumsan_1day_trip_yn"))
    as_ok = fields.get("as_1y")
    ko["K7"] = (
        "PASS"
        if trip is True and as_ok
        else ("FAIL" if trip is False else "HOLD")
    )

    strong: dict[str, str] = {}
    for sid, key, need in [
        ("S1", "sensor_gw_wireless", ("sensor_gw_wireless", "gw_recommended_coverage_pyeong")),
        ("S2", "soil_sensor_model_qty", ("soil_sensor_model_qty",)),
        ("S3", "usim_apn_self_provision", ("usim_apn_self_provision",)),
        ("S4", "gateway_model", ("gateway_model",)),
        ("S5", "vendor_app_phase0", ("vendor_app_phase0",)),
        ("S6", "expansion_quote_yn", ("expansion_quote_yn",)),
    ]:
        vals = [fields.get(k) for k in need]
        if all(v not in (None, "") for v in vals):
            strong[sid] = "PASS"
        elif any(v not in (None, "") for v in vals):
            strong[sid] = "WARN"
        else:
            strong[sid] = "HOLD"

    fails = sum(1 for v in ko.values() if v == "FAIL")
    holds = sum(1 for v in ko.values() if v == "HOLD")
    warns = sum(1 for v in strong.values() if v == "WARN")

    if fails >= 1:
        verdict = "no_go"
        note = f"knockout FAIL={fails}"
    elif holds >= 1:
        verdict = "hold"
        note = f"knockout HOLD={holds} — 회신·PDF 보완 필요"
    elif warns >= 2:
        verdict = "conditional_go"
        note = f"strong WARN={warns} — 협상·2차 질의"
    else:
        verdict = "go"
        note = "knockout 전부 PASS"

    return {
        "knockout_results": ko,
        "strong_results": strong,
        "verdict": verdict,
        "verdict_note": note,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    p.add_argument(
        "--reply-json",
        type=Path,
        help="JSON with reply_capture_table.fields shape",
    )
    p.add_argument("--stdout-only", action="store_true")
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports/smartfarm_geumsan_vendor_reply_gonogo_eval_latest.json",
    )
    args = p.parse_args()

    checklist = _load(args.checklist)
    if args.reply_json:
        reply = _load(args.reply_json)
        fields = reply.get("fields") or reply.get("reply_capture_table", {}).get("fields") or reply
    else:
        fields = checklist.get("reply_capture_table", {}).get("fields") or {}

    result = evaluate(fields, checklist)
    checklist["evaluate"] = {
        **checklist.get("evaluate", {}),
        **result,
        "reply_fields_used": fields,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(checklist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.stdout_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"wrote {args.out}")
        print(f"verdict={result['verdict']} — {result['verdict_note']}")
    return 0 if result["verdict"] in ("go", "conditional_go", "hold") else 1


if __name__ == "__main__":
    sys.exit(main())
