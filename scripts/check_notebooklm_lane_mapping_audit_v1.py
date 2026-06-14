#!/usr/bin/env python3
"""Audit NotebookLM lens → notebook UUID 1:1 mapping and pack allowlist isolation.

Offline only (no Google calls). SSOT: docs/NotebookLM_sources_manifest.md

  py scripts/check_notebooklm_lane_mapping_audit_v1.py
  py scripts/check_notebooklm_lane_mapping_audit_v1.py --strict-known-groups

Output: reports/notebooklm_lane_mapping_audit_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_MAP = ROOT / "docs/final/notebooklm_lens_pack_push_map_v1.template.json"
RUNTIME_MAP = ROOT / "reports/notebooklm_lens_packs_v1/notebook_ids.json"
RULES = ROOT / "docs/final/artifacts/notebooklm_lane_mapping_rules_v1.json"
OUT = ROOT / "reports/notebooklm_lane_mapping_audit_v1_latest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_notebooklm_lens_source_packs_v1 import PACKS  # noqa: E402


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _notebook_map_sources() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    if TEMPLATE_MAP.is_file():
        out.append(("template", TEMPLATE_MAP))
    if RUNTIME_MAP.is_file():
        out.append(("runtime", RUNTIME_MAP))
    return out


def _duplicate_uuid_violations(
    lens_to_id: dict[str, str],
    *,
    known_groups: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_uuid: dict[str, list[str]] = {}
    for lens, nb_id in lens_to_id.items():
        if not nb_id:
            continue
        by_uuid.setdefault(nb_id, []).append(lens)

    known_sets = {frozenset(g.get("lenses") or []) for g in known_groups}
    violations: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []

    for nb_id, lenses in sorted(by_uuid.items()):
        if len(lenses) < 2:
            continue
        row = {"notebook_id": nb_id, "lenses": sorted(lenses)}
        if frozenset(lenses) in known_sets:
            allowed.append({**row, "status": "known_shared_group"})
        else:
            violations.append({**row, "status": "unexpected_shared_notebook"})
    return violations, allowed


def _pack_path_violations(rules: dict[str, Any]) -> list[dict[str, Any]]:
    forbidden = rules.get("forbidden_path_substrings_in_lens") or {}
    violations: list[dict[str, Any]] = []
    for lens, rels in PACKS.items():
        bans = forbidden.get(lens) or []
        if not bans:
            continue
        for rel in rels:
            for sub in bans:
                if sub in rel.replace("\\", "/"):
                    violations.append(
                        {
                            "lens": lens,
                            "path": rel,
                            "forbidden_substring": sub,
                            "status": "forbidden_path_in_lens_pack",
                        }
                    )
    return violations


def _cross_lens_path_duplicates() -> list[dict[str, Any]]:
    by_path: dict[str, list[str]] = {}
    for lens, rels in PACKS.items():
        for rel in rels:
            by_path.setdefault(rel, []).append(lens)
    rows: list[dict[str, Any]] = []
    for rel, lenses in sorted(by_path.items()):
        if len(lenses) < 2:
            continue
        rows.append(
            {
                "path": rel,
                "lenses": sorted(lenses),
                "status": "shared_allowlist_path",
                "hint": "informational — verify manifest allows overlap",
            }
        )
    return rows


def audit(*, strict_known_groups: bool) -> dict[str, Any]:
    rules = _load_json(RULES) if RULES.is_file() else {}
    known_groups = list(rules.get("known_shared_notebook_groups") or [])

    map_audits: list[dict[str, Any]] = []
    all_violations: list[dict[str, Any]] = []
    all_allowed_shared: list[dict[str, Any]] = []

    for label, path in _notebook_map_sources():
        doc = _load_json(path)
        lens_map = doc.get("lens_notebook_id") or {}
        if not isinstance(lens_map, dict):
            map_audits.append({"source": label, "path": str(path), "ok": False, "error": "bad lens_notebook_id"})
            continue
        lens_to_id = {str(k): str(v).strip() for k, v in lens_map.items() if v}
        violations, allowed = _duplicate_uuid_violations(lens_to_id, known_groups=known_groups)
        # strict: still block unexpected shares; documented known_shared groups remain allowed
        all_violations.extend({**v, "map_source": label} for v in violations)
        all_allowed_shared.extend({**a, "map_source": label} for a in allowed)
        map_audits.append(
            {
                "source": label,
                "path": path.relative_to(ROOT).as_posix(),
                "lens_count": len(lens_to_id),
                "duplicate_violations": len(violations),
                "known_shared_groups": len(allowed),
            }
        )

    pack_violations = _pack_path_violations(rules)
    cross_lens = _cross_lens_path_duplicates()

    blocking = [v for v in all_violations if v.get("status") == "unexpected_shared_notebook"]
    blocking.extend(pack_violations)

    ok = len(blocking) == 0
    return {
        "schema": "notebooklm_lane_mapping_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "ok": ok,
        "blocking_violation_count": len(blocking),
        "map_audits": map_audits,
        "duplicate_notebook_violations": all_violations,
        "known_shared_notebook_groups": all_allowed_shared,
        "pack_forbidden_path_violations": pack_violations,
        "cross_lens_shared_paths": cross_lens,
        "rules_path": RULES.relative_to(ROOT).as_posix() if RULES.is_file() else None,
        "reproduce": "py scripts/check_notebooklm_lane_mapping_audit_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--strict-known-groups",
        action="store_true",
        help="Audit mode label (documented known_shared groups always allowed; blocks unexpected shares only).",
    )
    args = ap.parse_args()

    payload = audit(strict_known_groups=args.strict_known_groups)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": payload["ok"], "blocking": payload["blocking_violation_count"], "out": str(OUT)}, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
