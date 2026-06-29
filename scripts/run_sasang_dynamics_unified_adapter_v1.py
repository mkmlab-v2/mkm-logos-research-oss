#!/usr/bin/env python3
"""Run sasang dynamics unified adapter v1 (worktree B-track).

  py scripts/run_sasang_dynamics_unified_adapter_v1.py
  py scripts/run_sasang_dynamics_unified_adapter_v1.py --lens-json experiments/.../sasang_independent_lens_ablation_v1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "sasang-head-btrack"
DEFAULT_WS = Path(r"C:\workspace")
sys.path.insert(0, str(EXP))

from sasang_dynamics_unified_adapter_v1 import (  # noqa: E402
    build_unified_output,
    machine_readables_from_lens_doc,
)

DEFAULT_LENS = EXP / "artifacts/sasang_independent_lens_ablation_v1.json"
FALLBACK_LENS = DEFAULT_WS / "docs/final/artifacts/sasang_independent_lens_latest.json"
DEFAULT_OUT = EXP / "artifacts/sasang_dynamics_unified_ablation_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--workspace-root", type=Path, default=DEFAULT_WS)
    args = ap.parse_args()

    if not args.lens_json.is_file() and FALLBACK_LENS.is_file():
        args.lens_json = FALLBACK_LENS

    if not args.lens_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing lens: {args.lens_json}"}))
        return 1

    lens_doc = json.loads(args.lens_json.read_text(encoding="utf-8"))
    mr = machine_readables_from_lens_doc(lens_doc)
    if not mr:
        print(json.dumps({"ok": False, "error": "machine_readables not found in lens json"}))
        return 1

    out = build_unified_output(
        mr,
        workspace_root=args.workspace_root.resolve(),
        input_provenance={
            "lens_json": str(args.lens_json).replace("\\", "/"),
            "lens_schema": lens_doc.get("schema"),
        },
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "stress": out.get("stress_v1"), "stage": out.get("pathology_stage_v1")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
