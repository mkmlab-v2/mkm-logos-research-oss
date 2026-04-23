#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Canon Operations Lock Declaration v1",
        "",
        f"- generated_at_utc: {data.get('generated_at_utc')}",
        f"- lock_state: {data.get('lock_state')}",
        f"- lock_reason: {data.get('lock_reason')}",
        "",
        "## Change Protocol",
    ]
    for r in list(data.get("change_protocol") or []):
        lines.append(f"- {r}")
    lines.extend(["", "## Locked Profiles"])
    strict = data.get("locked_profiles", {}).get("strict", {})
    balanced = data.get("locked_profiles", {}).get("balanced", {})
    lines.append(f"- strict: {json.dumps(strict, ensure_ascii=False)}")
    lines.append(f"- balanced: {json.dumps(balanced, ensure_ascii=False)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Declare operational parameter lock from vFinal freeze baseline.")
    ap.add_argument(
        "--freeze-vfinal-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_operations_lock_declaration_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_operations_lock_declaration_v1.md",
    )
    args = ap.parse_args()

    freeze = _read_json(Path(args.freeze_vfinal_json))
    lock_state = "locked" if str(freeze.get("freeze_decision") or "") == "frozen" else "conditional"
    out = {
        "schema": "original_corpus_regime_singularity_canon_operations_lock_declaration_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lock_state": lock_state,
        "lock_reason": "vfinal_frozen" if lock_state == "locked" else "vfinal_not_frozen",
        "inputs": {"freeze_vfinal_json": str(args.freeze_vfinal_json)},
        "locked_profiles": {
            "strict": dict(freeze.get("strict_profile") or {}),
            "balanced": dict(freeze.get("balanced_profile") or {}),
        },
        "change_protocol": [
            "Any threshold/profile change requires recalibration ticket.",
            "Must attach generation diff evidence and go_no_go recomputation.",
            "Require one dry-run and one scheduler run verification before apply.",
        ],
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

