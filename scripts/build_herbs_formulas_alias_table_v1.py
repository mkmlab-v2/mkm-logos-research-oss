#!/usr/bin/env python3
"""Build and validate herbs_formulas_alias_table_v1 from curated seed (B-track)."""

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

from scripts.herbs_formulas_alias_table_v1 import TABLE_SCHEMA, normalize_alias  # noqa: E402

DEFAULT_SEED = ROOT / "data" / "herbs_formulas" / "herbs_formulas_alias_seed_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "herbs_formulas_alias_table_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _collect_alias_map(entries: list[dict[str, Any]], *, kind: str, id_key: str) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    for entry in entries:
        canonical_id = str(entry.get(id_key) or "")
        if not canonical_id:
            raise ValueError(f"{kind} entry missing {id_key}")
        names: list[str] = []
        for key in ("canonical_name_hans", "canonical_name_ko", "pinyin"):
            val = entry.get(key)
            if isinstance(val, str) and val.strip():
                names.append(val.strip())
        for alias in entry.get("aliases", []):
            if isinstance(alias, str) and alias.strip():
                names.append(alias.strip())
        for name in names:
            norm = normalize_alias(name)
            if not norm:
                continue
            prev = alias_map.get(norm)
            if prev and prev != canonical_id:
                raise ValueError(
                    f"alias collision: {norm!r} maps to both {prev!r} and {canonical_id!r}"
                )
            alias_map[norm] = canonical_id
    return alias_map


def validate_seed(seed: dict[str, Any]) -> dict[str, int]:
    herbs = seed.get("herbs", [])
    formulas = seed.get("formulas", [])
    if not isinstance(herbs, list) or not herbs:
        raise ValueError("seed must include non-empty herbs list")
    if not isinstance(formulas, list) or not formulas:
        raise ValueError("seed must include non-empty formulas list")

    herb_ids = {str(h["canonical_id"]) for h in herbs if h.get("canonical_id")}
    _collect_alias_map(herbs, kind="herb", id_key="canonical_id")
    _collect_alias_map(formulas, kind="formula", id_key="formula_id")

    for formula in formulas:
        formula_id = str(formula.get("formula_id") or "")
        if not formula.get("canonical_name_hans"):
            raise ValueError(f"formula {formula_id} missing canonical_name_hans")
        for row in formula.get("composition", []):
            herb_id = str(row.get("herb_id") or "")
            if herb_id not in herb_ids:
                raise ValueError(f"formula {formula_id} references unknown herb_id {herb_id!r}")

    return {"herb_count": len(herbs), "formula_count": len(formulas)}


def build_alias_table(seed: dict[str, Any], *, seed_path: Path) -> dict[str, Any]:
    stats = validate_seed(seed)
    return {
        "schema": TABLE_SCHEMA,
        "version": "1.1.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "track_b_only": True,
        "send_gate": "HOLD",
        "expert_review_required": True,
        "boundary_ack": (
            "Curated alias table from classical teaching seed; not a full materia medica index, "
            "not Logos lexicon, and not patient-facing prescription output."
        ),
        "provenance": {
            "seed_path": _posix_path(seed_path),
            "seed_schema": seed.get("schema"),
            "source_refs": list(seed.get("source_refs") or []),
            "herb_count": stats["herb_count"],
            "formula_count": stats["formula_count"],
            "curation_status": "seed_v1_expert_review_required",
        },
        "herbs": seed["herbs"],
        "formulas": seed["formulas"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build herbs_formulas alias table artifact")
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    seed_path = args.seed.resolve()
    if not seed_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing seed: {seed_path}"}, ensure_ascii=False))
        return 2

    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    try:
        doc = build_alias_table(seed, seed_path=seed_path)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_path": _posix_path(out_path),
                "herb_count": doc["provenance"]["herb_count"],
                "formula_count": doc["provenance"]["formula_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
