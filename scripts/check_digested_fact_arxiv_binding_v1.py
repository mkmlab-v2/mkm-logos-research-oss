#!/usr/bin/env python3
"""Validate explicit digested facts arxiv_id against binding registry (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/mkm_digested_arxiv_binding_registry_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_digested_arxiv_binding_check_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _normalize_arxiv(aid: str | None) -> str | None:
    if not aid:
        return None
    return str(aid).strip().replace("arXiv:", "").replace("arxiv:", "")


def check_bindings(
    doc: dict[str, Any],
    *,
    registry: dict[str, Any],
    source_path: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    bindings = registry.get("bindings") or []
    forbidden = registry.get("forbidden_misbindings") or []

    for fact in doc.get("facts") or []:
        prov = fact.get("provenance") or {}
        if prov.get("extraction_method") != "explicit_block":
            continue
        arm = str(fact.get("comparison_arm") or "")
        aid = _normalize_arxiv(prov.get("arxiv_id"))
        fact_id = str(fact.get("fact_id") or "")

        for fb in forbidden:
            needle = str(fb.get("comparison_arm_contains") or "")
            bad = _normalize_arxiv(fb.get("arxiv_id"))
            if needle and needle in arm and aid == bad:
                issues.append(
                    {
                        "severity": "error",
                        "fact_id": fact_id,
                        "comparison_arm": arm,
                        "arxiv_id": aid,
                        "reason": fb.get("reason"),
                        "source_path": source_path,
                    }
                )

        if not aid:
            for rule in bindings:
                needle = str(rule.get("comparison_arm_contains") or "")
                if needle and needle in arm:
                    issues.append(
                        {
                            "severity": "warn",
                            "fact_id": fact_id,
                            "comparison_arm": arm,
                            "arxiv_id": None,
                            "expected_arxiv_id": rule.get("arxiv_id"),
                            "reason": "explicit_block missing arxiv_id for known work",
                            "source_path": source_path,
                        }
                    )
                    break
            continue

        for rule in bindings:
            needle = str(rule.get("comparison_arm_contains") or "")
            expected = _normalize_arxiv(rule.get("arxiv_id"))
            if needle and needle in arm and expected and aid != expected:
                issues.append(
                    {
                        "severity": "error",
                        "fact_id": fact_id,
                        "comparison_arm": arm,
                        "arxiv_id": aid,
                        "expected_arxiv_id": expected,
                        "reason": f"arxiv mismatch for {rule.get('label') or needle}",
                        "source_path": source_path,
                    }
                )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Check digested fact arxiv bindings")
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict", action="store_true", help="Fail on warnings too")
    args = parser.parse_args()

    registry_path = args.registry.resolve()
    if not registry_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing registry: {registry_path}"}, ensure_ascii=False))
        return 2

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    all_issues: list[dict[str, Any]] = []

    for in_path in args.input:
        path = in_path.resolve()
        if not path.is_file():
            print(json.dumps({"ok": False, "error": f"missing input: {path}"}, ensure_ascii=False))
            return 2
        doc = json.loads(path.read_text(encoding="utf-8"))
        all_issues.extend(check_bindings(doc, registry=registry, source_path=_posix(path)))

    errors = [i for i in all_issues if i["severity"] == "error"]
    warns = [i for i in all_issues if i["severity"] == "warn"]
    ok = not errors and (not args.strict or not warns)

    report = {
        "schema": "mkm_digested_arxiv_binding_check_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "error_count": len(errors),
        "warn_count": len(warns),
        "issues": all_issues,
        "registry_path": _posix(registry_path),
        "research_only": True,
        "send_gate": "HOLD",
        "reproduce": "py scripts/check_digested_fact_arxiv_binding_v1.py --input <digested.json>",
    }
    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "error_count": len(errors), "warn_count": len(warns)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
