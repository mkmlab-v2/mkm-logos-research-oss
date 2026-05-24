#!/usr/bin/env python3
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZID = "259a847ea3643566383972ebd3ede918"


def _from_env_file(key: str) -> str:
    env = ROOT / ".env"
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _get(path: str, tok: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:
            return exc.code, {"errors": [{"message": str(exc)}]}


def main() -> int:
    for key in ("MKM_MKMLIFE_CF_ANALYTICS_TOKEN", "CLOUDFLARE_API_TOKEN"):
        tok = _from_env_file(key)
        if not tok:
            print(f"{key}: missing")
            continue
        fp = f"{tok[:6]}...{tok[-4:]}"
        _, v = _get("/user/tokens/verify", tok)
        _, z = _get(f"/zones/{ZID}", tok)
        print(
            f"{key} fp={fp} verify={v.get('success')} "
            f"zone={z.get('success')} errs={z.get('errors')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
