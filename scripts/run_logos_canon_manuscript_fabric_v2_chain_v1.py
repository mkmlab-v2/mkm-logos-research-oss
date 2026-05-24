#!/usr/bin/env python3
"""One-shot chain: gap policy classify (if present) -> fabric v2 -> optional wire profile extension."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    rc = subprocess.run(cmd, cwd=str(ROOT))
    return int(rc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-classify", action="store_true")
    ap.add_argument("--skip-fabric", action="store_true")
    ap.add_argument("--extend-wire-poc", action="store_true", help="Annotate graph wire PoC with gap routing sample")
    args = ap.parse_args()
    py = sys.executable

    steps: list[tuple[str, list[str]]] = []
    if not args.skip_classify:
        policy = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
        if policy.is_file():
            steps.append(
                (
                    "classify",
                    [py, str(ROOT / "scripts/build_logos_gap_mt_only_residual_classify_v1.py")],
                )
            )
    if not args.skip_fabric:
        steps.append(("fabric_v2", [py, str(ROOT / "scripts/build_logos_canon_manuscript_fabric_v2.py")]))

    for name, cmd in steps:
        code = _run(cmd)
        if code != 0:
            print(json.dumps({"ok": False, "failed_step": name, "exit_code": code}))
            return code

    if args.extend_wire_poc:
        fabric_path = ROOT / "docs/final/artifacts/logos_canon_manuscript_fabric_v2_latest.json"
        poc_path = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
        if fabric_path.is_file() and poc_path.is_file():
            fabric = json.loads(fabric_path.read_text(encoding="utf-8"))
            poc = json.loads(poc_path.read_text(encoding="utf-8"))
            gap_ids = (fabric.get("canonical_address_layer") or {}).get("gap_verse_ids") or []
            cal = fabric.get("canonical_address_layer") or {}
            poc["manuscript_fabric_v2_ref"] = {
                "path": "docs/final/artifacts/logos_canon_manuscript_fabric_v2_latest.json",
                "gap_nt_textual_variant_count": cal.get("gap_nt_textual_variant_count"),
                "gap_sample_verse_ids": gap_ids[:3],
                "routing_flag_bit": (fabric.get("wire_routing") or {}).get("flag_re_route_tr_bit"),
            }
            poc_path.write_text(json.dumps(poc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "steps": [s[0] for s in steps]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
