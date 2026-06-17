#!/usr/bin/env python3
"""Verify a-codeai open-bench payload binding on benchmark pages (live or staging)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "docs/final/artifacts/a_codeai_open_bench_binding_check_latest.json"
LEGAL_SIGNOFF = ROOT / "docs/final/artifacts/compression_b2b_legal_send_signoff_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fetch_text(url: str, timeout: float) -> tuple[bool, str]:
    req = Request(
        url,
        headers={
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (compatible; MKM-AcodeaiOpenBenchBinding/1.0)",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return True, resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, ValueError):
        return False, ""


def _legal_send_open() -> bool:
    if not LEGAL_SIGNOFF.is_file():
        return False
    try:
        doc = json.loads(LEGAL_SIGNOFF.read_text(encoding="utf-8"))
    except Exception:
        return False
    return (
        str(doc.get("send_gate", "")).upper() == "OPEN"
        and bool(doc.get("ready_for_external_send", False))
    )


def _check_bench_payload(body: str) -> tuple[bool, dict[str, Any]]:
    details: dict[str, Any] = {
        "json_parse_ok": False,
        "schema_ok": False,
        "send_gate": None,
        "send_gate_ok": False,
    }
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        return False, details
    details["json_parse_ok"] = True
    schema_ok = str(doc.get("schema")) == "a_codeai_public_bench_landing_payload_v1"
    details["schema_ok"] = schema_ok
    send_gate = str(doc.get("send_gate", "")).upper()
    details["send_gate"] = send_gate
    legal_open = _legal_send_open()
    details["legal_send_open"] = legal_open
    gate_ok = send_gate == "HOLD" or (send_gate == "OPEN" and legal_open)
    details["send_gate_ok"] = gate_ok
    details["public_sku_count"] = len((doc.get("sections") or {}).get("public_skus") or [])
    ok = schema_ok and gate_ok and details["public_sku_count"] >= 3
    return ok, details


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="https://a-codeai.com")
    ap.add_argument("--timeout-sec", type=float, default=12.0)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    payload_url = f"{base}/a_codeai_public_bench_landing_payload_v1_latest.json"
    ko_bench_url = f"{base}/ko/benchmark/"
    en_bench_url = f"{base}/benchmark/"

    page_markers = [
        "a_codeai_public_bench_landing_payload_v1_latest.json",
        "open-bench-section",
        "open-bench-sku-table",
    ]

    payload_ok, payload_body = _fetch_text(payload_url, args.timeout_sec)
    payload_contract_ok, payload_details = (
        _check_bench_payload(payload_body) if payload_ok else (False, {"reason": "payload_unreachable"})
    )

    ko_ok, ko_body = _fetch_text(ko_bench_url, args.timeout_sec)
    en_ok, en_body = _fetch_text(en_bench_url, args.timeout_sec)
    ko_markers_ok = all(m in ko_body for m in page_markers) if ko_ok else False
    en_markers_ok = all(m in en_body for m in page_markers) if en_ok else False

    all_ok = bool(payload_ok and payload_contract_ok and ko_ok and en_ok and ko_markers_ok and en_markers_ok)
    decision = "PASS" if all_ok else "FAIL"

    out_doc: dict[str, Any] = {
        "schema": "a_codeai_open_bench_binding_check_v1",
        "generated_at_utc": _now_utc(),
        "target": {
            "base_url": base,
            "payload_url": payload_url,
            "ko_benchmark_url": ko_bench_url,
            "en_benchmark_url": en_bench_url,
        },
        "all_ok": all_ok,
        "decision": decision,
        "checks": {
            "payload": {
                "reachable": payload_ok,
                "contract_ok": payload_contract_ok,
                "details": payload_details,
            },
            "ko_benchmark": {"reachable": ko_ok, "markers_ok": ko_markers_ok},
            "en_benchmark": {"reachable": en_ok, "markers_ok": en_markers_ok},
        },
        "notes": [
            "FAIL until VPS deploy copies bench payload + updated benchmark HTML templates.",
            "Run: bash scripts/deploy/linux/deploy_a_codeai_landing_from_repo.sh",
        ],
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "all_ok": all_ok, "decision": decision, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
