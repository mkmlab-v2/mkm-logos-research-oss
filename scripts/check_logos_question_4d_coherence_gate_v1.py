#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gate: question router 4D shadow mean coherence >= threshold [HYPO][NON_GATING]."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
OUT = ROOT / "reports/logos_question_4d_coherence_gate_v1_latest.json"


def _load_shadow_mod():
    spec = importlib.util.spec_from_file_location(
        "logos_question_4d_shadow_v1",
        ROOT / "scripts/logos_question_4d_shadow_v1.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--min-mean", type=float, default=0.5)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    router_path = args.router_json if args.router_json.is_absolute() else ROOT / args.router_json
    if not router_path.is_file():
        doc = {"schema": "logos_question_4d_coherence_gate_v1", "ok": False, "error": "router_missing"}
        args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(doc, ensure_ascii=False))
        return 2

    mod = _load_shadow_mod()
    router = json.loads(router_path.read_text(encoding="utf-8-sig"))
    gate = mod.coherence_gate_check(router, min_mean=args.min_mean)
    try:
        gate["router_path"] = str(router_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        gate["router_path"] = str(router_path)
    gate["checked_at_utc"] = mod._utc_now()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": gate.get("ok"), "mean": gate.get("mean_four_d_coherence")}, ensure_ascii=False))
    return 0 if gate.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
