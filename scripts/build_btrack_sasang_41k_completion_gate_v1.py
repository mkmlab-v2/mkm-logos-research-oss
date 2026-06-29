#!/usr/bin/env python3
"""B-track Sasang-41k HD chain completion gate [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/btrack_sasang_41k_completion_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> dict[str, Any]:
    chain = _load(ROOT / "reports/btrack_sasang_41k_hd_chain_v1_latest.json")
    shadow = _load(ROOT / "reports/btrack_sasang_lexicon_shadow_v1_latest.json")
    gate = _load(ROOT / "reports/btrack_sasang_role_mismatch_gate_v1_latest.json")
    psi_bridge = _load(ROOT / "reports/btrack_sasang_psi_role_bridge_v1_latest.json")

    checks: list[dict[str, Any]] = []

    def _add(cid: str, ok: bool, weight: int, note: str = "") -> None:
        checks.append({"check_id": cid, "pass": bool(ok), "weight": weight, "note": note})

    _add("shadow_written", shadow.get("schema") == "btrack_sasang_lexicon_shadow_v1", 20)
    _add("codebook_unmodified", shadow.get("codebook_unmodified") is True, 20)
    _add("track_a_bridge_false", shadow.get("track_a_bridge") is False, 10)
    _add("mismatch_gate_pass", (gate.get("summary") or {}).get("gate_pass") is True, 15)
    _add("psi_bridge_ok", psi_bridge.get("bridge_ok") is True, 15)
    _add(
        "lexicon_rows_ge_1k",
        int(shadow.get("codebook_entry_count") or 0) >= 1000,
        10,
        f"rows={shadow.get('codebook_entry_count')}",
    )
    _add(
        "four_roles_present",
        len([k for k, v in (shadow.get("role_counts") or {}).items() if int(v or 0) > 0]) >= 4,
        10,
    )

    earned = sum(c["weight"] for c in checks if c["pass"])
    total = sum(c["weight"] for c in checks)
    score = round(100.0 * earned / total, 1) if total else 0.0
    target = 90.0

    return {
        "schema": "btrack_sasang_41k_completion_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "non_gating": True,
        "track_a_bridge": False,
        "completion_score": score,
        "completion_target": target,
        "completion_pass": score >= target,
        "checks": checks,
        "reproduce_cmd": "py scripts/build_btrack_sasang_41k_completion_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["completion_pass"], "score": doc["completion_score"], "out": str(args.out)},
            ensure_ascii=False,
        )
    )
    return 0 if doc["completion_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
