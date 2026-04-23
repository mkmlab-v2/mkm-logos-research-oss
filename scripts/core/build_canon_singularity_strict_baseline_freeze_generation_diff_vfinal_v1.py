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


def _diff(prefix: str, a: Any, b: Any, out: list[dict[str, Any]]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a.keys()) | set(b.keys())):
            p = f"{prefix}.{k}" if prefix else k
            _diff(p, a.get(k), b.get(k), out)
        return
    if a != b:
        out.append({"field": prefix, "from": a, "to": b})


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Canon Strict Baseline Freeze Generation Diff vFinal v1",
        "",
        f"- generated_at_utc: {data.get('generated_at_utc')}",
        f"- total_change_count: {data.get('total_change_count')}",
        "",
    ]
    sections = data.get("sections") or {}
    for key in ("v1_to_v2", "v2_to_vfinal", "v1_to_vfinal"):
        rows = list((sections.get(key) or {}).get("changes") or [])
        lines.append(f"## {key} ({len(rows)})")
        if not rows:
            lines.append("- none")
        else:
            for r in rows:
                lines.append(f"- {r['field']}: {r['from']} -> {r['to']}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _collect(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "freeze_decision": obj.get("freeze_decision"),
        "profile": obj.get("profile") or obj.get("strict_profile") or {},
        "balanced_profile": obj.get("balanced_profile") or {},
        "gate_status": obj.get("gate_status") or {},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build generation diff across freeze v1/v2/vFinal snapshots.")
    ap.add_argument(
        "--freeze-v1-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v1.json",
    )
    ap.add_argument(
        "--freeze-v2-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2.json",
    )
    ap.add_argument(
        "--freeze-vfinal-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_generation_diff_vfinal_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_generation_diff_vfinal_v1.md",
    )
    args = ap.parse_args()

    v1 = _collect(_read_json(Path(args.freeze_v1_json)))
    v2 = _collect(_read_json(Path(args.freeze_v2_json)))
    vf = _collect(_read_json(Path(args.freeze_vfinal_json)))

    d12: list[dict[str, Any]] = []
    d2f: list[dict[str, Any]] = []
    d1f: list[dict[str, Any]] = []
    _diff("", v1, v2, d12)
    _diff("", v2, vf, d2f)
    _diff("", v1, vf, d1f)

    out = {
        "schema": "original_corpus_regime_singularity_canon_strict_baseline_freeze_generation_diff_vfinal_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "freeze_v1_json": str(args.freeze_v1_json),
            "freeze_v2_json": str(args.freeze_v2_json),
            "freeze_vfinal_json": str(args.freeze_vfinal_json),
        },
        "sections": {
            "v1_to_v2": {"change_count": len(d12), "changes": d12},
            "v2_to_vfinal": {"change_count": len(d2f), "changes": d2f},
            "v1_to_vfinal": {"change_count": len(d1f), "changes": d1f},
        },
        "total_change_count": len(d12) + len(d2f) + len(d1f),
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

