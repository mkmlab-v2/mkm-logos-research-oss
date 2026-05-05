#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_operational_smoke_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(path: Path, predicate, fail_reason: str) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "path": str(path), "reason": "missing_file"}
    try:
        data = _read_json(path)
    except Exception:
        return {"ok": False, "path": str(path), "reason": "invalid_json"}
    ok = bool(predicate(data))
    return {"ok": ok, "path": str(path), "reason": "ok" if ok else fail_reason}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    checks = []
    checks.append(
        _check(
            ART / "pointerguard_folder_policy_latest.json",
            lambda d: str(d.get("schema", "")) == "pointerguard_folder_policy_v1",
            "invalid_policy_schema",
        )
    )
    checks.append(
        _check(
            ART / "pointerguard_apply_go_promotion_decision_latest.json",
            lambda d: str(d.get("decision", "")) in {"PROMOTE_APPLY_GO", "KEEP_SHADOW"},
            "invalid_router_target_decision",
        )
    )
    checks.append(
        _check(
            ART / "pointerguard_apply_go_promotion_decision_memory_latest.json",
            lambda d: str(d.get("decision", "")) in {"PROMOTE_APPLY_GO", "KEEP_SHADOW"},
            "invalid_memory_decision",
        )
    )
    checks.append(
        _check(
            ART / "pointerguard_memory_v2_ramp_freeze_latest.json",
            lambda d: bool(d.get("ramp_frozen", False))
            and int(d.get("ramp_current_index", -1)) == int(d.get("ramp_max_index", -2)),
            "memory_ramp_not_frozen_at_max",
        )
    )
    checks.append(
        _check(
            ART / "genesis_pointer_route_runtime_config_latest.json",
            lambda d: bool(d.get("promotion_gate", {}).get("apply_go_enabled", False)),
            "runtime_promotion_gate_not_enabled",
        )
    )

    all_ok = all(bool(c.get("ok", False)) for c in checks)
    out_doc = {
        "schema": "pointerguard_operational_smoke_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "all_ok": all_ok,
        "checks": checks,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "out": str(out_path)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
