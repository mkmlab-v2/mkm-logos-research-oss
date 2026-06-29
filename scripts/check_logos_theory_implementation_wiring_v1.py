#!/usr/bin/env python3
"""Validate Logos theory→implementation wiring registry (re-invention guard)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/logos_theory_implementation_wiring_v1.json"
SCRIPTS_DIR = ROOT / "scripts"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel_exists(rel: str) -> bool:
    return (ROOT / rel.replace("/", "\\")).is_file() or (ROOT / rel).is_file()


def check_registry(doc: dict[str, Any], *, strict_aliases: bool) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != "logos_theory_implementation_wiring_v1":
        errors.append("schema mismatch")
    edges = doc.get("canonical_edges") or []
    if not edges:
        errors.append("canonical_edges empty")

    script_names = {p.name for p in SCRIPTS_DIR.rglob("*.py")}
    for edge in edges:
        edge_id = edge.get("edge_id", "?")
        for key in (
            "implementation_scripts",
            "theory_artifacts",
            "implementation_artifacts",
            "ui_wire",
        ):
            for rel in edge.get(key) or []:
                if not _rel_exists(rel):
                    errors.append(f"{edge_id}: missing {rel}")
        stats = edge.get("stats_artifact")
        if stats and not _rel_exists(stats):
            errors.append(f"{edge_id}: missing stats {stats}")

        if strict_aliases:
            for alias in edge.get("forbidden_aliases") or []:
                alias_py = f"{alias}.py" if not alias.endswith(".py") else alias
                if alias_py in script_names:
                    errors.append(
                        f"{edge_id}: forbidden alias script exists: {alias_py} "
                        f"(extend edge {edge_id} instead)"
                    )

    prod = next((e for e in edges if e.get("edge_id") == "production_gematria_kernel"), None)
    sandbox = next((e for e in edges if e.get("edge_id") == "spread_sandbox_research"), None)
    if prod and sandbox:
        must_not = sandbox.get("must_not_replace")
        if must_not and must_not not in json.dumps(prod, ensure_ascii=False):
            errors.append("production edge must document gematria_bridge_v1 guard")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict-aliases", action="store_true", default=True)
    parser.add_argument("--no-strict-aliases", action="store_true")
    args = parser.parse_args()
    strict_aliases = args.strict_aliases and not args.no_strict_aliases

    if not args.registry.is_file():
        print(f"FAIL: missing {args.registry}", file=sys.stderr)
        return 1

    doc = _load(args.registry)
    errors = check_registry(doc, strict_aliases=strict_aliases)
    report = {
        "ok": not errors,
        "registry": str(args.registry.relative_to(ROOT)).replace("\\", "/"),
        "edge_count": len(doc.get("canonical_edges") or []),
        "errors": errors,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
    else:
        print(f"OK: logos_theory_implementation_wiring_v1 edges={report['edge_count']}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
