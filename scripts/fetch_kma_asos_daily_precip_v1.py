#!/usr/bin/env python3
"""Fetch KMA ASOS daily precipitation via data.go.kr (B-track resolve helper)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DOTENV = ROOT / ".env"
DEFAULT_STATION_ID = "108"
DEFAULT_STATION_ROW_ID = "seoul_asos_108"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def parse_sum_rn_mm(sum_rn: Any) -> float:
    if sum_rn is None:
        return 0.0
    token = str(sum_rn).strip()
    if token in ("", "-", "-9.0", "-9", "null", "None", "NA"):
        return 0.0
    return float(token)


def _parse_items(doc: dict[str, Any]) -> list[dict[str, Any]]:
    header = (doc.get("response") or {}).get("header") or {}
    if str(header.get("resultCode")) not in ("00", "0", "0000"):
        return []
    body = (doc.get("response") or {}).get("body") or {}
    items = body.get("items")
    if items is None:
        return []
    if isinstance(items, dict):
        raw = items.get("item")
    else:
        raw = items
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    return []


def _request_asos(*, stn_id: str, start_yyyymmdd: str, end_yyyymmdd: str, timeout: float) -> dict[str, Any]:
    key = _service_key()
    if not key:
        return {"ok": False, "error": "no_service_key"}
    params = {
        "serviceKey": key,
        "numOfRows": "999",
        "pageNo": "1",
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "DAY",
        "startDt": start_yyyymmdd,
        "endDt": end_yyyymmdd,
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
    items = _parse_items(doc)
    return {"ok": True, "items": items, "api_header": header}


def item_to_fetch_summary(item: dict[str, Any]) -> dict[str, Any]:
    sum_rn = item.get("sumRn")
    precip = parse_sum_rn_mm(sum_rn)
    tm = str(item.get("tm") or "")[:10]
    return {
        "ok": True,
        "stnId": item.get("stnId"),
        "stnNm": item.get("stnNm"),
        "tm": tm,
        "sumRn": sum_rn,
        "precip_mm": precip,
        "ge_1mm": precip >= 1.0,
    }


def item_to_ground_truth_row(
    item: dict[str, Any],
    *,
    station_row_id: str = DEFAULT_STATION_ROW_ID,
    threshold_mm: float = 0.1,
) -> dict[str, Any]:
    tm = str(item.get("tm") or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", tm):
        raise ValueError(f"invalid asos tm: {item.get('tm')!r}")
    precip = parse_sum_rn_mm(item.get("sumRn"))
    max_ta = item.get("maxTa")
    temp_max: float | None
    if max_ta in (None, "", "-"):
        temp_max = None
    else:
        temp_max = float(max_ta)
    doc: dict[str, Any] = {
        "schema": "weather_ground_truth_row_v1",
        "observation_date_local": tm,
        "timezone": "Asia/Seoul",
        "station_or_region_id": station_row_id,
        "precip_mm_day": round(precip, 4),
        "precip_binary_gt_0_1mm": precip > threshold_mm,
        "temp_max_c": temp_max,
        "source": {
            "retrieved_at_utc": _utc_now(),
            "dataset_name": "kma_asos_daly_info_v1",
            "stn_id": str(item.get("stnId") or DEFAULT_STATION_ID),
            "evidence_uri": "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList",
        },
    }
    payload = "|".join([tm, station_row_id, f"{precip:.4f}"])
    doc["row_fingerprint"] = f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"
    return doc


def fetch_asos_daily(*, stn_id: str, yyyymmdd: str, timeout: float = 30.0) -> dict[str, Any]:
    doc = _request_asos(stn_id=stn_id, start_yyyymmdd=yyyymmdd, end_yyyymmdd=yyyymmdd, timeout=timeout)
    if not doc.get("ok"):
        return doc
    items = doc.get("items") or []
    if not items:
        return {"ok": False, "error": "no_item", "api_header": doc.get("api_header")}
    out = item_to_fetch_summary(items[0])
    out["api_header"] = doc.get("api_header")
    return out


def fetch_asos_daily_range(
    *,
    stn_id: str,
    start_yyyymmdd: str,
    end_yyyymmdd: str,
    timeout: float = 45.0,
) -> dict[str, Any]:
    doc = _request_asos(
        stn_id=stn_id,
        start_yyyymmdd=start_yyyymmdd,
        end_yyyymmdd=end_yyyymmdd,
        timeout=timeout,
    )
    if not doc.get("ok"):
        return doc
    rows = [item_to_fetch_summary(item) for item in (doc.get("items") or [])]
    return {
        "ok": True,
        "stn_id": stn_id,
        "start": start_yyyymmdd,
        "end": end_yyyymmdd,
        "n_items": len(rows),
        "rows": rows,
        "api_header": doc.get("api_header"),
    }


def yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stn-id", default=DEFAULT_STATION_ID)
    ap.add_argument("--date", help="YYYYMMDD (single day)")
    ap.add_argument("--start-date", help="YYYYMMDD")
    ap.add_argument("--end-date", help="YYYYMMDD")
    ap.add_argument("--days", type=int, default=0, help="If set, ending yesterday KST back N days")
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()
    _load_dotenv()

    if args.date:
        doc = fetch_asos_daily(stn_id=args.stn_id, yyyymmdd=args.date)
    elif args.start_date and args.end_date:
        doc = fetch_asos_daily_range(
            stn_id=args.stn_id,
            start_yyyymmdd=args.start_date,
            end_yyyymmdd=args.end_date,
        )
    elif args.days > 0:
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=max(1, args.days) - 1)
        doc = fetch_asos_daily_range(
            stn_id=args.stn_id,
            start_yyyymmdd=yyyymmdd(start),
            end_yyyymmdd=yyyymmdd(end),
        )
    else:
        print("provide --date or --start-date/--end-date or --days", file=sys.stderr)
        return 2

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
