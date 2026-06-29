#!/usr/bin/env python3
"""Deploy jemaai-robots-v1 worker + route jemaai.cloud/robots.txt (needs Workers Routes Edit)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402

ACCOUNT = "646e42cf881ab43043c32430e99d9af4"
ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
SCRIPT = "jemaai-robots-v1"
OUT = ROOT / "reports" / "cloudflare_jemaai_robots_worker_v1_latest.json"

WORKER_JS = b"""
const ORIGIN = `User-agent: *
Disallow: /legacy/
Allow: /
`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname !== "/robots.txt") {
      return fetch(request);
    }
    const resp = await fetch(request);
    const managed = await resp.text();
    if (managed.includes("Disallow: /legacy/")) {
      return new Response(managed, { headers: { "content-type": "text/plain; charset=utf-8" } });
    }
    const body = managed.trimEnd() + "\\n\\n" + ORIGIN.trim() + "\\n";
    return new Response(body, { headers: { "content-type": "text/plain; charset=utf-8" } });
  }
};
"""


def _api(tok: str, method: str, path: str, data: bytes | None = None, content_type: str | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


def main() -> int:
    tok, src = resolve_cloudflare_token()
    doc: dict = {
        "schema": "cloudflare_jemaai_robots_worker_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token_source": src,
    }
    if not tok:
        doc["error"] = "no_token"
        OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return 1

    # Upload worker (ES module)
    boundary = "mkmrobotsboundary"
    meta = json.dumps({"main_module": "worker.mjs", "compatibility_date": "2024-01-01"}).encode()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="metadata"; filename="metadata.json"\r\n'
        f"Content-Type: application/json\r\n\r\n"
    ).encode() + meta + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="worker.mjs"; filename="worker.mjs"\r\n'
        f"Content-Type: application/javascript+module\r\n\r\n"
    ).encode() + WORKER_JS + f"\r\n--{boundary}--\r\n".encode()

    st, pl = _api(
        tok,
        "PUT",
        f"/accounts/{ACCOUNT}/workers/scripts/{SCRIPT}",
        data=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    doc["upload"] = {"http": st, "success": pl.get("success"), "errors": pl.get("errors")}

    route_body = json.dumps({"pattern": "jemaai.cloud/robots.txt", "script": SCRIPT}).encode()
    st2, pl2 = _api(tok, "POST", f"/zones/{ZONE_ID}/workers/routes", data=route_body, content_type="application/json")
    doc["route"] = {"http": st2, "success": pl2.get("success"), "errors": pl2.get("errors"), "result": pl2.get("result")}

    try:
        with urllib.request.urlopen("https://jemaai.cloud/robots.txt", timeout=30) as resp:
            text = resp.read().decode()
        doc["verify"] = {"legacy_disallow": "Disallow: /legacy/" in text}
    except Exception as exc:
        doc["verify"] = {"error": str(exc), "legacy_disallow": False}

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = bool(doc.get("verify", {}).get("legacy_disallow"))
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
