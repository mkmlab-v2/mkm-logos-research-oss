#!/usr/bin/env python3
"""Rewrite mkmlife pixel sprite_url entries — local relative vs CDN dual-mode.

  local: /pixel_battalion/refined/*.png  (workspace disk gate)
  cdn:   https://assets.jemaai.cloud/pixel_battalion/refined/*.png  (deploy)

  py scripts/apply_mkmlife_pixel_language_local_sprite_paths_v1.py --mode local
  py scripts/apply_mkmlife_pixel_language_local_sprite_paths_v1.py --mode cdn
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PIXEL_JSON = ROOT / "projects/mkm/mkm-life/public/data/MKM_PIXEL_LANGUAGE_V1.json"
DEFAULT_REPORT = ROOT / "reports/mkmlife_pixel_language_local_paths_v1_latest.json"

CDN_PREFIX = "https://assets.jemaai.cloud/pixel_battalion/refined/"
LOCAL_PREFIX = "/pixel_battalion/refined/"
Mode = Literal["local", "cdn"]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _filename_from_url(url: str) -> str | None:
    m = re.search(r"/([^/]+\.png)$", url.strip(), re.I)
    return m.group(1) if m else None


def rewrite_sprite_url(url: str, mode: Mode) -> tuple[str, bool]:
    u = url.strip()
    fn = _filename_from_url(u)
    if not fn:
        return u, False
    target = f"{CDN_PREFIX}{fn}" if mode == "cdn" else f"{LOCAL_PREFIX}{fn}"
    if u == target:
        return u, False
    return target, True


def apply_paths(doc: dict[str, Any], mode: Mode) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    for reg_key in ("category_sprite_registry", "morning_beans_lane_registry"):
        reg = doc.get(reg_key) or {}
        if not isinstance(reg, dict):
            continue
        for key, entry in reg.items():
            if not isinstance(entry, dict):
                continue
            old = entry.get("sprite_url")
            if not isinstance(old, str) or not old.strip():
                continue
            new, changed = rewrite_sprite_url(old, mode)
            if changed:
                entry["sprite_url"] = new
                changes.append(
                    {"registry": reg_key, "key": str(key), "from": old, "to": new}
                )
    deploy = doc.setdefault("sprite_deploy_mode", {})
    if isinstance(deploy, dict):
        deploy.update(
            {
                "mode": mode,
                "cdn_base": "https://assets.jemaai.cloud",
                "local_public_prefix": LOCAL_PREFIX,
                "updated_at_utc": _utc(),
                "hypothesis_tag": "[HYPO]",
            }
        )
    return changes


def detect_mode(doc: dict[str, Any]) -> str | None:
    deploy = doc.get("sprite_deploy_mode") or {}
    if isinstance(deploy, dict) and deploy.get("mode") in ("local", "cdn"):
        return str(deploy["mode"])
    for reg_key in ("category_sprite_registry", "morning_beans_lane_registry"):
        reg = doc.get(reg_key) or {}
        if not isinstance(reg, dict):
            continue
        for entry in reg.values():
            if not isinstance(entry, dict):
                continue
            url = entry.get("sprite_url")
            if isinstance(url, str) and url.startswith(LOCAL_PREFIX):
                return "local"
            if isinstance(url, str) and url.startswith(CDN_PREFIX):
                return "cdn"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pixel-json", type=Path, default=DEFAULT_PIXEL_JSON)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--mode", choices=("local", "cdn"), default="local")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pixel_path = args.pixel_json.resolve()
    if not pixel_path.is_file():
        print(f"error: missing {pixel_path}", file=sys.stderr)
        return 2

    doc = json.loads(pixel_path.read_text(encoding="utf-8-sig"))
    changes = apply_paths(doc, args.mode)
    report = {
        "schema": "mkmlife_pixel_language_local_paths_v1",
        "generated_at_utc": _utc(),
        "pixel_json": _rel(pixel_path),
        "mode": args.mode,
        "detected_mode_before": detect_mode(doc) if not changes else args.mode,
        "change_count": len(changes),
        "changes": changes,
        "hypothesis_tag": "[HYPO]",
        "note": "Use --mode local for workspace gate; --mode cdn before mkmlife CDN deploy.",
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if not args.dry_run:
        pixel_path.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "mode": args.mode,
                "change_count": len(changes),
                "dry_run": args.dry_run,
                "out": _rel(args.report_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
