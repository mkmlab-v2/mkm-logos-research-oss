#!/usr/bin/env python3
"""Gate: domain_prophecy_registry_v1 + config files validate and paths exist.

Writes reports/domain_prophecy_registry_gate_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"
REGISTRY_SCHEMA = ROOT / "docs/final/schemas/domain_prophecy_registry_v1.schema.json"
CONFIG_SCHEMA = ROOT / "docs/final/schemas/domain_prophecy_config_v1.schema.json"
OUT = ROOT / "reports/domain_prophecy_registry_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema not installed"]
    schema = _load_json(schema_path)
    try:
        jsonschema.validate(instance=doc, schema=schema)
    except jsonschema.ValidationError as exc:
        return [str(exc.message)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    if not args.registry.is_file():
        print(f"FAIL: missing registry {args.registry}", file=sys.stderr)
        return 1

    registry = _load_json(args.registry)
    errors.extend(_validate(registry, REGISTRY_SCHEMA))

    for domain in registry.get("domains") or []:
        domain_id = str(domain.get("domain_id") or "?")
        config_rel = domain.get("config_path")
        if config_rel:
            config_path = ROOT / str(config_rel).replace("/", "\\")
            ok = config_path.is_file()
            checks.append({"kind": "config", "domain_id": domain_id, "path": config_rel, "ok": ok})
            if not ok:
                errors.append(f"missing config for {domain_id}: {config_rel}")
                continue
            config_doc = _load_json(config_path)
            if config_doc.get("domain_id") != domain_id:
                errors.append(f"domain_id mismatch in {config_rel}: {config_doc.get('domain_id')}")
            cfg_errors = _validate(config_doc, CONFIG_SCHEMA)
            for msg in cfg_errors:
                errors.append(f"{domain_id} config schema: {msg}")
        for legacy in domain.get("legacy_config_paths") or []:
            legacy_path = ROOT / str(legacy).replace("/", "\\")
            ok = legacy_path.is_file()
            checks.append({"kind": "legacy", "domain_id": domain_id, "path": legacy, "ok": ok})
            if not ok:
                errors.append(f"missing legacy path for {domain_id}: {legacy}")
        for script_key in ("loop_script", "smoke_script"):
            rel = domain.get(script_key)
            if not rel:
                continue
            script_path = ROOT / str(rel).replace("/", "\\")
            ok = script_path.is_file()
            checks.append({"kind": script_key, "domain_id": domain_id, "path": rel, "ok": ok})
            if not ok:
                errors.append(f"missing {script_key} for {domain_id}: {rel}")

    schedule_rel = str(registry.get("schedule_pointer") or "")
    if schedule_rel:
        schedule_ok = (ROOT / schedule_rel.replace("/", "\\")).is_file()
        checks.append({"kind": "schedule_pointer", "path": schedule_rel, "ok": schedule_ok})
        if not schedule_ok:
            errors.append(f"missing schedule_pointer: {schedule_rel}")

    ok = not errors
    report = {
        "schema": "domain_prophecy_registry_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "registry_path": str(args.registry.relative_to(ROOT)).replace("\\", "/"),
        "domain_count": len(registry.get("domains") or []),
        "config_validated_count": sum(1 for c in checks if c.get("kind") == "config" and c.get("ok")),
        "errors": errors,
        "checks": checks,
        "reproduce": "py scripts/check_domain_prophecy_registry_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "domain_count": report["domain_count"], "errors": len(errors)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
