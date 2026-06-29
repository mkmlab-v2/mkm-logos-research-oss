#!/usr/bin/env python3
"""[HYPO] Solapi alimtalk dry payloads from B2B training spec — no live API send."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/final/artifacts/gwangmyeong_baekje_b2b_training_spec_v1.json"
OUT = ROOT / "docs/final/artifacts/gwangmyeong_baekje_b2b_solapi_dry_v1_latest.json"

SAMPLE_VARS = {
    "이름": "홍길동",
    "정적_허브_URL": "https://drive.google.com/folder/PLACEHOLDER_HUB",
    "과제_폼_URL": "https://forms.gle/PLACEHOLDER_ASSIGNMENT",
    "주차": "2주차",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _substitute(text: str, variables: dict[str, str]) -> str:
    out = text
    for key, value in variables.items():
        out = out.replace(f"#{{{key}}}", value)
    return out


def _resolve_buttons(buttons: list[dict[str, Any]], variables: dict[str, str]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for btn in buttons:
        item = dict(btn)
        if "url" in item:
            item["url"] = _substitute(str(item["url"]), variables)
        if "name" in item:
            item["name"] = _substitute(str(item["name"]), variables)
        resolved.append(item)
    return resolved


def _unresolved_placeholders(text: str) -> list[str]:
    return sorted(set(re.findall(r"#\{([^}]+)\}", text)))


def _build_template_dry(key: str, tpl: dict[str, Any], variables: dict[str, str]) -> dict[str, Any]:
    header = _substitute(str(tpl.get("header") or ""), variables)
    body = _substitute(str(tpl.get("body") or ""), variables)
    buttons = _resolve_buttons(list(tpl.get("buttons") or []), variables)
    full_text = f"{header}\n{body}".strip()
    unresolved = _unresolved_placeholders(full_text + json.dumps(buttons, ensure_ascii=False))
    return {
        "template_key": key,
        "resolved_header": header,
        "resolved_body": body,
        "resolved_buttons": buttons,
        "resolved_preview": full_text,
        "unresolved_placeholders": unresolved,
        "solapi_request_shape": {
            "message": {
                "to": "DRY_RUN_TO",
                "from": "DRY_RUN_FROM",
                "type": "ATA",
                "text": full_text,
                "kakaoOptions": {
                    "pfId": "PLACEHOLDER_PF_ID",
                    "templateId": f"PLACEHOLDER_TEMPLATE_{key.upper()}",
                    "buttons": buttons,
                },
            }
        },
    }


def build(spec: dict[str, Any]) -> dict[str, Any]:
    talk = spec.get("automated_talk_loop_4weeks") or {}
    templates = talk.get("templates") or {}
    dry_templates = [
        _build_template_dry(key, tpl, SAMPLE_VARS) for key, tpl in sorted(templates.items())
    ]
    any_unresolved = any(t["unresolved_placeholders"] for t in dry_templates)
    return {
        "schema": "gwangmyeong_baekje_b2b_solapi_dry_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "live_send": False,
        "ready_for_external_send": False,
        "spec_pointer": str(SPEC.relative_to(ROOT)).replace("\\", "/"),
        "dealer_api_target": talk.get("dealer_api_target", "Solapi_REST_v1"),
        "phase": talk.get("phase", 2),
        "sample_variables": SAMPLE_VARS,
        "templates_dry": dry_templates,
        "ok": not any_unresolved,
        "reproduce": "py scripts/build_gwangmyeong_baekje_b2b_solapi_dry_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SPEC.is_file():
        print(json.dumps({"ok": False, "error": f"missing {SPEC}"}))
        return 2

    doc = build(json.loads(SPEC.read_text(encoding="utf-8")))
    if args.dry_run:
        print(json.dumps({"ok": doc["ok"], "templates": len(doc["templates_dry"])}, ensure_ascii=False))
        return 0 if doc["ok"] else 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
