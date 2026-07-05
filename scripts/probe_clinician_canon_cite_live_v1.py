#!/usr/bin/env python3
"""Live probe: clinic.no1kmedi.com canon cite API (MKM_WORKSPACE_ROOT + lookup script)."""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "clinician_canon_cite_live_probe_v1_latest.json"

BASE = "https://clinic.no1kmedi.com"
QUERY = "태양인"


def main() -> int:
    url = f"{BASE}/api/clinician/canon-cite-v1?q={urllib.parse.quote(QUERY)}&limit=2"
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-clinician-canon-cite-probe/1"})
    row: dict = {"url": url, "ok": False}
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=35, context=ctx) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            row["status"] = resp.status
            data = json.loads(body)
            row["success"] = data.get("success")
            row["hit_count"] = data.get("hit_count")
            row["chunk_ids"] = [
                c.get("chunk_id") for c in (data.get("chunks") or []) if c.get("chunk_id")
            ]
            row["ok"] = bool(data.get("success")) and row["hit_count"] and len(row["chunk_ids"]) >= 1
    except urllib.error.HTTPError as e:
        row["status"] = e.code
        row["body"] = e.read(2000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, ssl.SSLError, TimeoutError, json.JSONDecodeError) as e:
        row["error"] = str(e)[:300]

    out = {
        "schema": "clinician_canon_cite_live_probe_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "all_ok": bool(row.get("ok")),
        "probe": row,
        "reproduce": "py scripts/probe_clinician_canon_cite_live_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
