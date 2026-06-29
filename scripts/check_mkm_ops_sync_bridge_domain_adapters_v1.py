#!/usr/bin/env python3
"""Gate: mkm_ops_sync_bridge_v1 domain_adapters pointers exist on disk.

Writes reports/mkm_ops_sync_bridge_domain_adapters_gate_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "docs/final/artifacts/mkm_ops_sync_bridge_v1.json"
OUT = ROOT / "reports/mkm_ops_sync_bridge_domain_adapters_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _collect_paths(adapter: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for key in (
        "ssot_assets",
        "ssot_schemas",
        "scripts",
        "gate_scripts",
        "smoke_scripts",
    ):
        for item in adapter.get(key) or []:
            rows.append((key, str(item)))
    for key in ("gate_report", "charter_pointer"):
        val = adapter.get(key)
        if val:
            rows.append((key, str(val)))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bridge", type=Path, default=BRIDGE)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.bridge.is_file():
        print(f"FAIL: missing bridge {args.bridge}", file=sys.stderr)
        return 1

    bridge = json.loads(args.bridge.read_text(encoding="utf-8-sig"))
    section = bridge.get("domain_adapters") or {}
    adapters = section.get("adapters") or []
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    for top_key in (
        "ops_memory_overlay_builder",
        "pointer_gate_script",
        "one_click_smoke_ps1",
    ):
        rel = str(section.get(top_key) or "").strip()
        if not rel:
            errors.append(f"domain_adapters missing {top_key}")
            continue
        path = ROOT / rel.replace("/", "\\")
        ok = path.is_file()
        checks.append({"kind": "section_script", "key": top_key, "path": rel, "ok": ok})
        if not ok:
            errors.append(f"missing section script: {rel}")

    for adapter in adapters:
        aid = str(adapter.get("id") or "unknown")
        for kind, rel in _collect_paths(adapter):
            path = ROOT / rel.replace("/", "\\")
            ok = path.is_file()
            checks.append(
                {
                    "adapter_id": aid,
                    "kind": kind,
                    "path": rel,
                    "ok": ok,
                }
            )
            if not ok:
                errors.append(f"{aid}: missing {kind}: {rel}")

    doc = {
        "schema": "mkm_ops_sync_bridge_domain_adapters_gate_v1",
        "generated_at_utc": _utc(),
        "bridge": _rel(args.bridge),
        "adapter_count": len(adapters),
        "ok": not errors,
        "errors": errors,
        "checks": checks,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "research_only": True,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(args.out), "errors": len(errors)}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
