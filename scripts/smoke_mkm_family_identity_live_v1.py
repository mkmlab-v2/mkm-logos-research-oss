#!/usr/bin/env python3
"""Live smoke: MKM Family identity endpoints on app.jema-ai.com (no OAuth round-trip)."""

from __future__ import annotations

import json
import sys
import urllib.request

ORIGIN = "https://app.jema-ai.com"
UA = "Mozilla/5.0 (compatible; mkm-smoke/1.0)"


def get_json(path: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{ORIGIN}{path}",
        headers={"User-Agent": UA, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body)


def main() -> int:
    issues: list[str] = []
    checks: list[dict] = []

    for path, expect_keys in (
        ("/api/mkm-family/session", ("ok", "configured", "authenticated")),
        ("/hub", None),
        ("/auth/mkm-callback", None),
    ):
        try:
            req = urllib.request.Request(f"{ORIGIN}{path}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                code = resp.status
                if path.endswith("session"):
                    data = json.loads(resp.read().decode("utf-8"))
                    for k in expect_keys or ():
                        if k not in data:
                            issues.append(f"{path}: missing key {k}")
                    checks.append({"path": path, "status": code, "session": data})
                else:
                    checks.append({"path": path, "status": code})
                if code not in (200, 301, 302, 307, 308):
                    issues.append(f"{path}: unexpected status {code}")
        except Exception as exc:
            issues.append(f"{path}: {exc}")

    try:
        code, data = get_json("/api/mkm-family/session")
        if not data.get("ok"):
            issues.append("session: ok!=true")
        checks.append({"id": "session_json", "status": code, "configured": data.get("configured")})
    except Exception as exc:
        issues.append(f"session_json: {exc}")

    out = {"origin": ORIGIN, "overall_ok": not issues, "issues": issues, "checks": checks}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
