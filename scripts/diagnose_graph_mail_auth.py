#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import base64
from urllib import parse, request


def req_token() -> str:
    tid = os.environ["GRAPH_TENANT_ID"].strip()
    cid = os.environ["GRAPH_CLIENT_ID"].strip()
    sec = os.environ["GRAPH_CLIENT_SECRET"].strip()
    data = parse.urlencode(
        {
            "client_id": cid,
            "client_secret": sec,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
    ).encode("utf-8")
    r = request.Request(
        f"https://login.microsoftonline.com/{tid}/oauth2/v2.0/token",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with request.urlopen(r, timeout=20) as resp:  # nosec B310
        doc = json.loads(resp.read().decode("utf-8"))
    return str(doc.get("access_token", ""))


def call(path: str, token: str) -> tuple[int, str]:
    req = request.Request(
        f"https://graph.microsoft.com/v1.0/{path}",
        method="GET",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with request.urlopen(req, timeout=20) as resp:  # nosec B310
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = str(e)
        return int(e.code), body


def main() -> int:
    token = req_token()
    if not token:
        print("token: missing")
        return 1
    print("token: acquired")
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
        print("token.roles:", claims.get("roles"))
        print("token.appid:", claims.get("appid"))
        print("token.tid:", claims.get("tid"))
    except Exception as exc:
        print("token.decode.error:", exc)
    for p in ["organization", "users?$top=1"]:
        status, body = call(p, token)
        print(f"{p}: {status}")
        print(body[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

