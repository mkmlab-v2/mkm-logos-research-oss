#!/usr/bin/env python3
"""Phase12 live URL bundle: jemaai + mkmlife envelope probe ([HYPO] smoke only)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_phase12_live_bundle_v1_latest.json"

URLS: dict[str, str] = {
    "oracle_v6_product": "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1",
    "meaning_topology_html": "https://jemaai.cloud/public_showroom_meaning_topology_graph_v1.html",
    "meaning_topology_json": "https://jemaai.cloud/showroom_meaning_topology_graph_slice_v1.json",
    "chronology_overlay": "https://jemaai.cloud/showroom_logos_chronology_overlay_v1.json",
    "trace_health": "https://api.jemaai.cloud/v1/logos/health",
    "mkmlife_envelope": "https://mkmlife.com/data/three_lens_sphere_envelope_v1.json",
}


def _head_or_get(url: str, timeout: float = 20.0) -> dict:
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method)
        req.add_header("User-Agent", "mkm-logos-phase12-live/1")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = b"" if method == "HEAD" else resp.read(8192)
                ct = resp.headers.get("content-type", "")
                return {
                    "url": url,
                    "method": method,
                    "http_status": int(resp.status),
                    "content_type": ct,
                    "body_bytes": len(body),
                    "ok": resp.status == 200,
                }
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue
            return {"url": url, "method": method, "http_status": e.code, "ok": False, "error": str(e)}
        except Exception as e:
            return {"url": url, "method": method, "http_status": None, "ok": False, "error": str(e)}
    return {"url": url, "ok": False, "error": "unreachable"}


def main() -> int:
    steps: dict[str, object] = {}
    errors: list[str] = []
    for key, url in URLS.items():
        row = _head_or_get(url)
        steps[key] = row
        if not row.get("ok"):
            # mkmlife envelope may lag deploy — warn not fail closure for optional host
            if key == "mkmlife_envelope":
                row["optional"] = True
                row["note"] = "local copy ok; public 200 may require mkmlife deploy"
                continue
            errors.append(f"{key}: not ok ({row.get('http_status')})")

    envelope_schema_ok = False
    mk = steps.get("mkmlife_envelope")
    if isinstance(mk, dict) and mk.get("ok") and mk.get("method") == "GET":
        try:
            req = urllib.request.Request(URLS["mkmlife_envelope"], method="GET")
            req.add_header("User-Agent", "mkm-logos-phase12-live/1")
            with urllib.request.urlopen(req, timeout=20) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
                envelope_schema_ok = doc.get("schema") == "three_lens_sphere_envelope_v1"
                if not envelope_schema_ok:
                    errors.append("mkmlife_envelope: schema mismatch")
        except Exception as e:
            errors.append(f"mkmlife_envelope parse: {e}")

    local_env = ROOT / "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_v1.json"
    local_ok = local_env.is_file()
    local_schema_ok = False
    if local_ok:
        doc = json.loads(local_env.read_text(encoding="utf-8-sig"))
        local_schema_ok = doc.get("schema") == "three_lens_sphere_envelope_v1"

    doc = {
        "schema": "logos_phase12_live_bundle_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "steps": steps,
        "local_mkmlife_copy": {
            "path": str(local_env.relative_to(ROOT)),
            "present": local_ok,
            "schema_ok": local_schema_ok,
        },
        "mkmlife_public_schema_ok": envelope_schema_ok,
        "jemaai_core_ok": all(
            isinstance(steps.get(k), dict) and steps[k].get("ok")
            for k in (
                "oracle_v6_product",
                "meaning_topology_html",
                "meaning_topology_json",
            )
        ),
        "errors": errors,
        "ok": len(errors) == 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "jemaai_core_ok": doc["jemaai_core_ok"], "errors": errors}, ensure_ascii=False))
    return 0 if doc["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
