#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify L2 shadow readiness gates.

Checks:
1) memory drift latest has orphan_count=0 and ghost_count=0
2) l2 shadow latest has side_by_side_only + forbidden guards
3) pointer paths exist (workspace-relative)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def _missing_paths(workspace: Path, paths: List[str]) -> List[str]:
    out: List[str] = []
    for p in paths:
        pp = Path(p)
        if not pp.is_absolute():
            pp = workspace / pp
        if not pp.exists():
            out.append(p)
    return out


def main() -> int:
    wr = _workspace_root()
    ap = argparse.ArgumentParser(description="Verify L2 shadow readiness gates.")
    ap.add_argument(
        "--audit-path",
        type=Path,
        default=wr / "reports" / "memory" / "mkm_index_drift_audit_latest.json",
    )
    ap.add_argument(
        "--shadow-path",
        type=Path,
        default=wr / "reports" / "l2" / "l2_logos_shadow_latest.json",
    )
    args = ap.parse_args()

    audit = _load_json(args.audit_path)
    shadow = _load_json(args.shadow_path)

    checks: Dict[str, bool] = {}
    checks["drift_orphan_zero"] = int(audit.get("orphan_count", -1)) == 0
    checks["drift_ghost_zero"] = int(audit.get("ghost_count", -1)) == 0
    checks["junction_side_by_side"] = (
        (shadow.get("junction") or {}).get("mode") == "side_by_side_only"
    )
    forbidden = (shadow.get("junction") or {}).get("forbidden") or []
    checks["forbidden_single_field_fusion"] = "single_field_fusion" in forbidden
    checks["forbidden_verse_plus_ohlc_same_prompt"] = "verse_plus_ohlc_same_prompt" in forbidden

    pointers: List[str] = []
    pointers += (shadow.get("track_a_logos") or {}).get("pointer_paths") or []
    pointers += (shadow.get("track_b_episode") or {}).get("fact_pointers") or []
    missing = _missing_paths(wr, [p for p in pointers if isinstance(p, str)])
    checks["pointer_paths_exist"] = len(missing) == 0

    all_green = all(checks.values())
    result = {
        "all_green": all_green,
        "checks": checks,
        "missing_paths": missing,
        "audit_path": str(args.audit_path),
        "shadow_path": str(args.shadow_path),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all_green else 1


if __name__ == "__main__":
    raise SystemExit(main())
