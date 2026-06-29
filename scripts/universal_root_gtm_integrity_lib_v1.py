#!/usr/bin/env python3
"""Phase 1A integrity gates for UR GTM FREEZE [HYPO · HOLD]."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
B0_SPEC = ROOT / "docs/final/artifacts/universal_root_baseline_b0_spec_v1.json"
PHASE1A = ROOT / "reports/universal_root_phase1a_baseline_compare_v1_latest.json"
PHASE1A_ALIAS = ROOT / "reports/baseline_vs_dual_plane_v1.json"
LEXICON_AUDIT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_hf_checkpoint_v1_latest.json"
PUBLIC_README = ROOT / "exports/mkm-universal-root-v1/README.md"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def recompute_b0_english_only_rate(audit: dict[str, Any], crosswalk: dict[str, Any] | None = None) -> float | None:
    if crosswalk and crosswalk.get("rows"):
        from scripts.build_universal_root_phase1a_baseline_compare_v1 import (  # noqa: WPS433
            recompute_b0_english_only_rate as _from_crosswalk,
        )

        return _from_crosswalk(crosswalk, audit)
    baseline = audit.get("baseline") or {}
    rows = baseline.get("rows") or []
    non_control = int(baseline.get("non_control_pairs") or 0)
    if non_control <= 0:
        return None
    en_hits = sum(
        1
        for row in rows
        if str(row.get("control") or "") != "negative" and bool(row.get("en_hit"))
    )
    return round(en_hits / non_control, 4)


def _method_by_id(doc: dict[str, Any], mid: str) -> dict[str, Any] | None:
    for m in doc.get("methods") or []:
        if m.get("id") == mid:
            return m
    return None


def _readme_contains_pct(readme: str, value: float | None) -> bool:
    if value is None:
        return False
    needle = _pct(value)
    return needle in readme


def evaluate_phase1a_integrity(
    *,
    spec: dict[str, Any] | None = None,
    phase1a: dict[str, Any] | None = None,
    audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = spec if spec is not None else _read_json(B0_SPEC)
    violations: list[str] = []
    checks: dict[str, Any] = {}

    canonical = ROOT / str(spec.get("phase1a_canonical_artifact") or PHASE1A.name)
    alias = ROOT / str(spec.get("phase1a_alias_artifact") or PHASE1A_ALIAS.name)
    fixture = ROOT / str(spec.get("fixture_path") or "")
    readme = ROOT / str(spec.get("public_readme") or PUBLIC_README)

    if not canonical.is_file():
        violations.append("phase1a_canonical_artifact_missing")
    if not alias.is_file():
        violations.append("phase1a_alias_artifact_missing")

    checks["canonical_exists"] = canonical.is_file()
    checks["alias_exists"] = alias.is_file()

    if fixture.is_file():
        digest = _sha256_file(fixture)
        expected = str(spec.get("fixture_sha256") or "")
        checks["fixture_sha256"] = digest
        if expected and digest != expected:
            violations.append("fixture_sha256_mismatch")
    else:
        violations.append("fixture_missing")

    if phase1a is None and canonical.is_file():
        phase1a = _read_json(canonical)
    phase1a = phase1a or {}

    if phase1a.get("schema") != "universal_root_phase1a_baseline_compare_v1":
        violations.append("phase1a_schema_mismatch")

    required = list(spec.get("required_method_ids") or [])
    present = {m.get("id") for m in phase1a.get("methods") or []}
    for mid in required:
        if mid not in present:
            violations.append(f"missing_method_{mid}")

    b0 = _method_by_id(phase1a, "B0") or {}
    if b0.get("primary_metric") != spec.get("b0_definition", {}).get("primary_metric"):
        violations.append("b0_metric_definition_mismatch")

    if audit is None:
        audit = _read_json(LEXICON_AUDIT)
    crosswalk = _read_json(ROOT / "reports/universal_root_topology_crosswalk_v1_latest.json")
    recomputed = recompute_b0_english_only_rate(audit, crosswalk)
    checks["b0_recomputed"] = recomputed
    b0_val = b0.get("primary_value")
    tol = float(spec.get("recompute_tolerance") or 0.0001)
    if recomputed is None or b0_val is None:
        violations.append("b0_recompute_unavailable")
    elif abs(float(b0_val) - float(recomputed)) > tol:
        violations.append("b0_primary_value_not_recomputed_from_audit")

    b4 = _method_by_id(phase1a, "B4") or {}
    if b4.get("forbidden_headline") is not True:
        violations.append("b4_forbidden_headline_missing")

    readme_text = readme.read_text(encoding="utf-8-sig") if readme.is_file() else ""
    if not readme_text:
        violations.append("public_readme_missing")
    else:
        for mid in spec.get("readme_crosscheck_method_ids") or ["B0", "B3"]:
            method = _method_by_id(phase1a, mid) or {}
            val = method.get("primary_value")
            ok = _readme_contains_pct(readme_text, float(val) if val is not None else None)
            checks[f"readme_pct_{mid}"] = ok
            if not ok:
                violations.append(f"readme_missing_pct_{mid}")

    integrity_ok = not violations
    return {
        "schema": "universal_root_phase1a_integrity_eval_v1",
        "integrity_ok": integrity_ok,
        "violations": violations,
        "checks": checks,
        "b0_spec": str(B0_SPEC.relative_to(ROOT)).replace("\\", "/"),
        "canonical_artifact": str(canonical.relative_to(ROOT)).replace("\\", "/"),
        "alias_artifact": str(alias.relative_to(ROOT)).replace("\\", "/"),
    }
