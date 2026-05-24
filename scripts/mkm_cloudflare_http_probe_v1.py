"""HTTP edge probes for MKM Cloudflare ops (no secrets)."""
from __future__ import annotations

import re
import subprocess
from typing import Any


def probe_smartfarm_1hop() -> dict[str, Any]:
    """SSOT: https://jema-ai.com/smartfarm -> farm.jema-ai.com in one hop (no app.jema-ai.com)."""
    return _curl_probe(
        {
            "id": "smartfarm_1hop",
            "url": "https://jema-ai.com/smartfarm",
            "method": "HEAD",
            "expect_status": [301, 302, 307, 308],
            "expect_location_prefix": "https://farm.jema-ai.com",
            "forbid_location_contains": ["app.jema-ai.com/smartfarm"],
        }
    )


def _curl_probe(probe: dict[str, Any]) -> dict[str, Any]:
    url = probe["url"]
    method = probe.get("method", "HEAD")
    cmd = ["curl.exe", "-sSI", "-X", method, "--max-redirs", "0", url]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"id": probe.get("id"), "url": url, "ok": False, "error": str(e)}
    text = proc.stdout or ""
    status_m = re.search(r"HTTP/\S+\s+(\d+)", text)
    status = int(status_m.group(1)) if status_m else 0
    loc_m = re.search(r"(?i)^location:\s*(\S+)\s*$", text, re.MULTILINE)
    location = loc_m.group(1).strip() if loc_m else ""
    expect_status = set(probe.get("expect_status") or [200])
    ok = status in expect_status
    prefix = probe.get("expect_location_prefix")
    if prefix and location:
        ok = ok and location.startswith(prefix)
    for bad in probe.get("forbid_location_contains") or []:
        if bad and bad in location:
            ok = False
    return {
        "id": probe.get("id"),
        "url": url,
        "ok": ok,
        "http_status": status,
        "location": location,
        "exit_code": proc.returncode,
    }
