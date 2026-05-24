#!/usr/bin/env python3
"""One-off: verify CF tokens in .env (no secret output)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import resolve_cloudflare_token, token_fingerprint  # noqa: E402

KEYS = (
    "MKM_MKMLIFE_CF_ANALYTICS_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CF_API_TOKEN",
    "CLOUDFLARE_RULESETS_API_TOKEN",
    "MKM_CLOUDFLARE_PERSONADIARY_DNS_TOKEN",
)


def verify(tok: str) -> tuple[int, bool, dict]:
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/user/tokens/verify",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            j = json.loads(resp.read().decode())
            return resp.status, bool(j.get("success")), j
    except urllib.error.HTTPError as exc:
        try:
            j = json.loads(exc.read().decode())
        except Exception:
            j = {"errors": [{"message": str(exc), "code": exc.code}]}
        return exc.code, False, j


def main() -> int:
    env = ROOT / ".env"
    found: dict[str, str] = {}
    if env.is_file():
        for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if k in KEYS and v.strip():
                found[k] = v.strip().strip('"').strip("'")

    any_ok = False
    for k in KEYS:
        if k not in found:
            continue
        code, ok, j = verify(found[k])
        err = (j.get("errors") or [{}])[0]
        print(
            f"{k} fp={token_fingerprint(found[k])} verify_ok={ok} http={code} "
            f"err_code={err.get('code')} msg={str(err.get('message',''))[:80]}"
        )
        if ok:
            any_ok = True

    tok, src = resolve_cloudflare_token(extra_keys=("MKM_MKMLIFE_CF_ANALYTICS_TOKEN",))
    if tok:
        code, ok, j = verify(tok)
        print(f"resolve({src}) fp={token_fingerprint(tok)} verify_ok={ok} http={code}")
        if ok:
            any_ok = True

    return 0 if any_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
