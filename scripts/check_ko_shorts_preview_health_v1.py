#!/usr/bin/env python3
"""Ko shorts preview HTML + media path health (disk; optional HTTP when server up) [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_cursor_ide_qa_lib_v1 import _preview_media_src_v1  # noqa: E402

DEFAULT_HTML = ROOT / "reports/ko_shorts_cursor_preview_v1.html"
VIDEO_SRC_RE = re.compile(r'<video[^>]+src="([^"]+)"', re.IGNORECASE)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _port_listening(port: int) -> bool:
    try:
        import socket

        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _http_status(url: str, *, timeout_sec: float = 3.0) -> int | None:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception:
        return None


def _disk_path_for_src(src: str) -> Path:
    clean = _preview_media_src_v1(src)
    return ROOT / "reports" / clean


def check_ko_shorts_preview_health_v1(
    *,
    html_path: Path = DEFAULT_HTML,
    port: int = 8796,
    require_http: bool = False,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    media_rows: list[dict[str, Any]] = []

    if not html_path.is_file():
        return {
            "schema": "ko_shorts_preview_health_v1",
            "ok": False,
            "html_path": _rel(html_path),
            "issues": [{"kind": "html_missing"}],
            "media": [],
            "server_listening": _port_listening(port),
        }

    html = html_path.read_text(encoding="utf-8")
    srcs = VIDEO_SRC_RE.findall(html)
    if not srcs:
        issues.append({"kind": "no_video_src"})

    for raw_src in srcs:
        if raw_src.startswith("reports/"):
            issues.append({"kind": "double_reports_prefix", "src": raw_src})
        disk_path = _disk_path_for_src(raw_src)
        row: dict[str, Any] = {
            "video_src": raw_src,
            "disk_path": _rel(disk_path),
            "disk_exists": disk_path.is_file(),
        }
        if _port_listening(port):
            url_path = _preview_media_src_v1(raw_src)
            url = f"http://127.0.0.1:{port}/{url_path}"
            status = _http_status(url)
            row["http_url"] = url
            row["http_status"] = status
            if require_http and status != 200:
                issues.append({"kind": "http_not_ok", "url": url, "status": status})
        elif require_http:
            issues.append({"kind": "server_not_listening", "port": port})
        if not disk_path.is_file():
            issues.append({"kind": "media_missing", "path": _rel(disk_path)})
        media_rows.append(row)

    preview_url = f"http://127.0.0.1:{port}/ko_shorts_cursor_preview_v1.html"
    html_http_status = None
    if _port_listening(port):
        html_http_status = _http_status(preview_url)
        if require_http and html_http_status != 200:
            issues.append({"kind": "html_http_not_ok", "url": preview_url, "status": html_http_status})

    ok = len(issues) == 0
    return {
        "schema": "ko_shorts_preview_health_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "html_path": _rel(html_path),
        "preview_url": preview_url,
        "server_listening": _port_listening(port),
        "html_http_status": html_http_status,
        "issues": issues,
        "media": media_rows,
        "reproduce": f"py scripts/check_ko_shorts_preview_health_v1.py --port {port}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--port", type=int, default=8796)
    ap.add_argument("--require-http", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/ko_shorts_preview_health_v1_latest.json")
    args = ap.parse_args()

    html = args.html if args.html.is_absolute() else ROOT / args.html
    report = check_ko_shorts_preview_health_v1(
        html_path=html,
        port=args.port,
        require_http=args.require_http,
    )
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "out": _rel(out), "issues": report.get("issues")}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
