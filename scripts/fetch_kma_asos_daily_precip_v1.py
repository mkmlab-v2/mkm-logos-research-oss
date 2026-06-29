#!/usr/bin/env python3
"""Fetch KMA ASOS daily precipitation via data.go.kr (B-track resolve helper)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DOTENV = ROOT / ".env"


def _load_dotenv() -> None:
    if not DOTENV.is_file():
        return
    for raw in DOTENV.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and (key not in os.environ or not str(os.environ.get(key, "")).strip()):
            os.environ[key] = value


def _service_key() -> str:
    return (
        os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
        or os.getenv("PUBLIC_DATA_SERVICE_KEY", "").strip()
        or os.getenv("DATA_KMA_APIKEY", "").strip()
    )


def fetch_asos_daily(*, stn_id: str, yyyymmdd: str, timeout: float = 30.0) -> dict:
    key = _service_key()
    if not key:
        return {"ok": False, "error": "no_service_key"}
    params = {
        "serviceKey": key,
        "numOfRows": "10",
        "pageNo": "1",
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "DAY",
        "startDt": yyyymmdd,
        "endDt": yyyymmdd,
        "stnIds": stn_id,
    }
    url = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList?" + parse.urlencode(params)
    req = request.Request(url, headers={"User-Agent": "mkm-kma-asos-resolve/1.0"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        return {"ok": False, "http_status": exc.code, "body_preview": body}
    doc = json.loads(raw)
    header = (doc.get("response") or {}).get("header") or {}
    if str(header.get("resultCode")) not in ("00", "0", "0000"):
        return {"ok": False, "api_header": header, "raw_preview": raw[:400]}
    body = (doc.get("response") or {}).get("body") or {}
    items = body.get("items")
    item = None
    if isinstance(items, dict):
        item = items.get("item")
    elif isinstance(items, list):
        item = items[0] if items else None
    if isinstance(item, list):
        item = item[0] if item else None
    if not isinstance(item, dict):
        return {"ok": False, "error": "no_item", "api_header": header}
    sum_rn = item.get("sumRn")
    precip = None
    if sum_rn is not None and str(sum_rn).strip() not in ("", "-", "-9.0", "-9"):
        try:
            precip = float(sum_rn)
        except ValueError:
            precip = None
    return {
        "ok": True,
        "stnId": item.get("stnId"),
        "stnNm": item.get("stnNm"),
        "tm": item.get("tm"),
        "sumRn": sum_rn,
        "precip_mm": precip,
        "ge_1mm": bool(precip is not None and precip >= 1.0),
        "api_header": header,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stn-id", default="108")
    ap.add_argument("--date", required=True, help="YYYYMMDD")
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()
    _load_dotenv()
    doc = fetch_asos_daily(stn_id=args.stn_id, yyyymmdd=args.date)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
