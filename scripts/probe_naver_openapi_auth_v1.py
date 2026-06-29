#!/usr/bin/env python3
"""Probe Naver OpenAPI auth (news + datalab). Never prints secrets."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        if k and k not in os.environ:
            os.environ[k] = v.strip().strip('"').strip("'")


def _probe(url: str, *, method: str, hdr: dict[str, str], payload: dict | None = None) -> dict:
    data = None
    h = dict(hdr)
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    req = request.Request(url=url, method=method, headers=h, data=data)
    try:
        with request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return {"ok": True, "status": resp.status, "shape": type(json.loads(raw)).__name__}
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        return {"ok": False, "status": e.code, "reason": str(e.reason), "body_snip": body}


def main() -> int:
    _load_env()
    cid = os.environ.get("NAVER_CLIENT_ID", "").strip()
    csec = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
    expected = "k5_I2hLKrjvxbxvit8xU"
    out = {
        "client_id_set": bool(cid),
        "client_id_len": len(cid),
        "client_id_matches_console": cid == expected,
        "client_secret_set": bool(csec),
        "client_secret_len": len(csec),
        "probes": {},
    }
    if not cid or not csec:
        print(json.dumps({**out, "error": "missing_NAVER_CLIENT_ID_or_SECRET"}, ensure_ascii=False))
        return 2
    hdr = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec}
    news_q = parse.urlencode({"query": "대장", "display": 1, "sort": "date"})
    out["probes"]["search_news"] = _probe(
        f"https://openapi.naver.com/v1/search/news.json?{news_q}",
        method="GET",
        hdr=hdr,
    )
    from datetime import datetime, timedelta, timezone

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=7)
    datalab = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "keywordGroups": [{"groupName": "비트코인", "keywords": ["비트코인"]}],
        "device": "",
        "ages": [],
        "gender": "",
    }
    out["probes"]["datalab_search"] = _probe(
        "https://openapi.naver.com/v1/datalab/search",
        method="POST",
        hdr=hdr,
        payload=datalab,
    )
    news_ok = out["probes"].get("search_news", {}).get("ok")
    out["search_news_ready"] = bool(news_ok)
    out["hint_024"] = (
        "Scopes empty: add '검색' under 사용 API in Naver Developers API 설정 + WEB URL."
        if not news_ok
        else None
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if news_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
