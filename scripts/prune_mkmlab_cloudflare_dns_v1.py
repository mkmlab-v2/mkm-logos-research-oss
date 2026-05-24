"""Prune mkmlab.space Cloudflare DNS: drop stray apex A and all AAAA (LE/IPv6 hygiene)."""
from __future__ import annotations

import json
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ensure_mkmlab_space_cloudflare_dns_v1 import (  # noqa: E402
    DEFAULT_ORIGIN_IP,
    OUT as ENSURE_OUT,
    ZONE,
    _api,
    _list_records,
    _zone_id,
)
from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402

OUT = ROOT / "reports" / "prune_mkmlab_cloudflare_dns_latest.json"


def main() -> int:
    token, src = resolve_cloudflare_token()
    zid = _zone_id(token, "38a47f29983bd4ebce3798be08f59ba3")
    origin = DEFAULT_ORIGIN_IP
    actions: list[dict] = []

    for rec in _list_records(token, zid, "A", "@"):
        c = rec.get("content", "")
        if c != origin:
            _api(
                "DELETE",
                f"https://api.cloudflare.com/client/v4/zones/{zid}/dns_records/{rec['id']}",
                token,
            )
            actions.append({"deleted_a": c})

    import urllib.request

    for fq in (ZONE, f"www.{ZONE}"):
        url = (
            f"https://api.cloudflare.com/client/v4/zones/{zid}/dns_records"
            f"?type=AAAA&name={urllib.parse.quote(fq)}"
        )
        j = _api("GET", url, token)
        for rec in j.get("result") or []:
            _api(
                "DELETE",
                f"https://api.cloudflare.com/client/v4/zones/{zid}/dns_records/{rec['id']}",
                token,
            )
            actions.append({"deleted_aaaa": fq, "content": rec.get("content")})

    report = {
        "schema": "prune_mkmlab_cloudflare_dns_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "zone_id": zid,
        "token_source": src,
        "actions": actions,
        "ok": True,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "actions": len(actions)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
