#!/usr/bin/env python3
"""Resolve latest DART 사업보고서 rcept_no for a corp (Open DART list.json).

Default corp: 삼성전자 (00126380). Prefers 사업보고서 over 반기/분기 (MD&A body).

Reproduce:
  py scripts/resolve_dart_corp_mda_rcept_no_v1.py --corp-code 00126380
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_dart_mda_poc_env_v1 import dart_api_key  # noqa: E402

LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DEFAULT_CORP = "00126380"
DEFAULT_OUT = ROOT / "reports/kospi_dart_mda_rcept_resolve_v1_latest.json"

REPORT_HINTS = ("사업보고서", "반기보고서", "분기보고서")

REPORT_PRIORITY = (
    ("사업보고서", 0),
    ("반기보고서", 1),
    ("분기보고서", 2),
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _report_priority(report_nm: str) -> int:
    for hint, pri in REPORT_PRIORITY:
        if hint in report_nm:
            return pri
    return 9


def _fetch_list(api_key: str, corp_code: str, *, bgn_de: str, end_de: str) -> dict[str, Any]:
    params = urlencode(
        {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_count": "100",
            "page_no": "1",
        }
    )
    req = Request(f"{LIST_URL}?{params}", headers={"User-Agent": "MKM-KOSPI-DART-MDA-POC/1.0"})
    try:
        with urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except URLError as exc:
        raise RuntimeError(f"dart_list_fetch_failed: {exc}") from exc


def pick_latest_mda_report(list_doc: dict[str, Any]) -> dict[str, Any] | None:
    if str(list_doc.get("status")) != "000":
        message = str(list_doc.get("message") or "unknown")
        raise RuntimeError(f"dart_list_status: {list_doc.get('status')} {message}")
    rows = list_doc.get("list") or []
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("report_nm") or "")
        if any(h in name for h in REPORT_HINTS):
            candidates.append(row)
    if not candidates:
        return None
    candidates.sort(
        key=lambda r: (
            _report_priority(str(r.get("report_nm") or "")),
            -(int(str(r.get("rcept_dt") or "0") or 0)),
        ),
    )
    return candidates[0]


def resolve(corp_code: str, *, bgn_de: str, end_de: str) -> dict[str, Any]:
    api_key = dart_api_key()
    if not api_key:
        return {"ok": False, "error": "missing_DART_API_KEY", "skipped": True}
    list_doc = _fetch_list(api_key, corp_code, bgn_de=bgn_de, end_de=end_de)
    picked = pick_latest_mda_report(list_doc)
    if not picked:
        return {"ok": False, "error": "no_mda_report_in_window", "corp_code": corp_code}
    return {
        "ok": True,
        "schema": "kospi_dart_mda_rcept_resolve_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "corp_code": corp_code,
        "rcept_no": str(picked.get("rcept_no") or ""),
        "rcept_dt": str(picked.get("rcept_dt") or ""),
        "report_nm": str(picked.get("report_nm") or ""),
        "corp_name": str(picked.get("corp_name") or ""),
        "report_priority": _report_priority(str(picked.get("report_nm") or "")),
        "bgn_de": bgn_de,
        "end_de": end_de,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corp-code", default=DEFAULT_CORP)
    ap.add_argument("--bgn-de", default="20230101")
    ap.add_argument("--end-de", default="20261231")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    try:
        out = resolve(args.corp_code, bgn_de=args.bgn_de, end_de=args.end_de)
    except RuntimeError as exc:
        out = {"ok": False, "error": str(exc)}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    if out.get("skipped"):
        return 0
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
