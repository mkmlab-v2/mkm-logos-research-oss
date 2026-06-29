#!/usr/bin/env python3
"""Gate: every domain_prophecy registry row has smoke_script or loop_script on disk."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"
OUT = ROOT / "reports/domain_prophecy_smoke_coverage_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.registry.is_file():
        print(f"FAIL: missing {args.registry}", file=sys.stderr)
        return 1

    registry = json.loads(args.registry.read_text(encoding="utf-8-sig"))
    errors: list[str] = []
    rows: list[dict[str, Any]] = []

    for domain in registry.get("domains") or []:
        if not isinstance(domain, dict):
            continue
        domain_id = str(domain.get("domain_id") or "?")
        smoke = domain.get("smoke_script")
        loop = domain.get("loop_script")
        smoke_ok = False
        loop_ok = False
        if smoke:
            smoke_path = ROOT / str(smoke).replace("/", "\\")
            smoke_ok = smoke_path.is_file()
            if not smoke_ok:
                errors.append(f"{domain_id}: missing smoke_script {smoke}")
        else:
            errors.append(f"{domain_id}: missing smoke_script field")
        if loop:
            loop_path = ROOT / str(loop).replace("/", "\\")
            loop_ok = loop_path.is_file()
            if not loop_ok:
                errors.append(f"{domain_id}: missing loop_script {loop}")
        rows.append(
            {
                "domain_id": domain_id,
                "archetype": domain.get("archetype"),
                "phase": domain.get("phase"),
                "status": domain.get("status"),
                "smoke_script": smoke,
                "smoke_ok": smoke_ok,
                "loop_script": loop,
                "loop_ok": loop_ok,
            }
        )

    ok = not errors
    report = {
        "schema": "domain_prophecy_smoke_coverage_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "domain_count": len(rows),
        "smoke_mapped_count": sum(1 for r in rows if r.get("smoke_ok")),
        "errors": errors,
        "domains": rows,
        "reproduce": "py scripts/check_domain_prophecy_smoke_coverage_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "domain_count": len(rows), "errors": len(errors)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
