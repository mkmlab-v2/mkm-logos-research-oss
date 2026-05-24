#!/usr/bin/env python3
"""Live probe: mkmlife oracle-sphere + envelope JSON + jemaai v6 hub CTA markers."""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "magic_orb_live_probe_latest.json"
HISTORY = ROOT / "reports" / "magic_orb_live_probe_history.jsonl"

CHECKS = [
    {
        "id": "mkmlife_oracle",
        "url": "https://mkmlife.com/oracle-sphere",
        "markers": ["magic-orb-page", "마법구슬", "NON-MEDICAL", "magic-orb-disclaimer"],
        "max_bytes": 16384,
    },
    {
        "id": "mkmlife_envelope",
        "url": "https://mkmlife.com/data/three_lens_sphere_envelope_v1.json",
        "markers": ['"schema": "three_lens_sphere_envelope_v1"', '"hypothesis_tier": "B"'],
        "max_bytes": 8192,
    },
    {
        "id": "mkmlife_home",
        "url": "https://mkmlife.com/",
        "markers": ["oracle-sphere", "/oracle-sphere"],
        "max_bytes": 65536,
        "optional": True,
    },
    {
        "id": "jemaai_v6",
        "url": "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1",
        "markers": ["mkmlife.com/oracle-sphere", "Topology graph"],
        "max_bytes": 65536,
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(url: str, timeout: int = 25, max_bytes: int = 4096) -> tuple[int | None, str, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "MKM-probe-magic-orb/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(max_bytes).decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(2048).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return exc.code, body, str(exc)
    except Exception as exc:
        return None, "", str(exc)


def main() -> int:
    results: list[dict] = []
    for row in CHECKS:
        max_b = int(row.get("max_bytes") or 4096)
        status, body, err = _fetch(row["url"], max_bytes=max_b)
        missing = [m for m in row["markers"] if m not in body]
        core_ok = status is not None and 200 <= status < 400 and err is None
        markers_ok = not missing
        optional = bool(row.get("optional"))
        ok = core_ok and (markers_ok or optional)
        results.append(
            {
                "id": row["id"],
                "url": row["url"],
                "status": status,
                "markers": row["markers"],
                "missing_markers": missing,
                "optional": optional,
                "ok": ok,
                "error": err,
            }
        )

    all_ok = all(r["ok"] for r in results)
    doc = {
        "schema": "magic_orb_live_probe_v1",
        "checked_at_utc": _now(),
        "verdict_ko": "출구1+출구2 live OK" if all_ok else "일부 probe 실패",
        "results": results,
        "all_ok": all_ok,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    history_row = {
        "checked_at_utc": doc["checked_at_utc"],
        "all_ok": all_ok,
        "verdict_ko": doc["verdict_ko"],
        "results": [
            {
                "id": r["id"],
                "status": r["status"],
                "ok": r["ok"],
                "optional": r.get("optional", False),
            }
            for r in results
        ],
    }
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(history_row, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)} all_ok={all_ok}")
    print(f"Appended {HISTORY.relative_to(ROOT)}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
