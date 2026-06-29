#!/usr/bin/env python3
"""Fact-Lock gate for digested facts: schema + Right-verified wiring assertions."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_digested_facts_gate_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/mkm_research_digested_fact_v1.schema.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_field(doc: Any, field_path: str) -> Any:
    """Resolve methods.B3.primary_value style paths."""
    parts = field_path.split(".")
    cur: Any = doc
    for part in parts:
        if isinstance(cur, list):
            if part.isdigit():
                cur = cur[int(part)]
                continue
            for item in cur:
                if isinstance(item, dict) and str(item.get("id")) == part:
                    cur = item
                    break
            else:
                raise KeyError(f"id not found in list: {part}")
            continue
        if not isinstance(cur, dict):
            raise KeyError(f"cannot traverse {part!r} in non-dict")
        if part in cur:
            cur = cur[part]
            continue
        raise KeyError(f"missing field: {part}")
    return cur


def _compare(actual: float, expected: float, assertion: str) -> bool:
    if assertion == "lt":
        return actual < expected
    if assertion == "lte":
        return actual <= expected
    if assertion == "gt":
        return actual > expected
    if assertion == "gte":
        return actual >= expected
    if assertion == "eq":
        return actual == expected
    if assertion == "neq":
        return actual != expected
    raise ValueError(f"unknown assertion: {assertion}")


def run_gate(
    doc: dict[str, Any],
    *,
    strict_schema: bool = False,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    failures: list[str] = []

    if strict_schema:
        try:
            import jsonschema
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("jsonschema required for --strict-schema") from exc
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(instance=doc, schema=schema)

    for fact in doc.get("facts") or []:
        fact_id = str(fact.get("fact_id") or "")
        verification = fact.get("verification") or {}
        status = str(verification.get("status") or "Unknown")
        wiring = fact.get("mkm_wiring")

        entry: dict[str, Any] = {
            "fact_id": fact_id,
            "verification_status": status,
            "gate_status": "skipped",
        }

        if not wiring:
            entry["detail"] = "no mkm_wiring"
            entries.append(entry)
            continue

        if status != "Right":
            entry["detail"] = f"wiring present but verification={status}; assert skipped"
            entries.append(entry)
            continue

        artifact_rel = str(wiring.get("artifact_path") or "")
        artifact_path = (ROOT / artifact_rel).resolve()
        if not artifact_path.is_file():
            msg = f"{fact_id}: missing artifact {artifact_rel}"
            failures.append(msg)
            entry["gate_status"] = "fail"
            entry["detail"] = msg
            entries.append(entry)
            continue

        try:
            artifact_doc = json.loads(artifact_path.read_text(encoding="utf-8"))
            actual = float(resolve_field(artifact_doc, str(wiring["artifact_field"])))
            threshold = float(fact["value"])
            assertion = str(wiring["assertion"])
            passed = _compare(actual, threshold, assertion)
        except Exception as exc:
            msg = f"{fact_id}: resolve/compare failed: {exc}"
            failures.append(msg)
            entry["gate_status"] = "fail"
            entry["detail"] = msg
            entries.append(entry)
            continue

        entry["gate_status"] = "pass" if passed else "fail"
        entry["actual_value"] = actual
        entry["threshold"] = threshold
        entry["assertion"] = assertion
        if not passed:
            msg = (
                f"{fact_id}: actual {actual} vs threshold {threshold} "
                f"assertion {assertion} FAILED"
            )
            failures.append(msg)
            entry["detail"] = msg
        else:
            entry["detail"] = "assertion passed"
        entries.append(entry)

    ok = len(failures) == 0
    return {
        "schema": "mkm_digested_facts_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "failures": failures,
        "entries": entries,
        "research_only": True,
        "send_gate": "HOLD",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate digested facts wiring assertions")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict-schema", action="store_true")
    args = parser.parse_args()

    in_path = args.input.resolve()
    if not in_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {in_path}"}, ensure_ascii=False))
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    try:
        result = run_gate(doc, strict_schema=args.strict_schema)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": result["ok"],
                "out_path": _posix_path(out_path),
                "failures": result["failures"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
