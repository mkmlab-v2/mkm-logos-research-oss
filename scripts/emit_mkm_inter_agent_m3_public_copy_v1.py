#!/usr/bin/env python3
"""Emit M3 human-decoder public copy artifact from L1 inverse-decoder spike (research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

L1_SPIKE = ROOT / "docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_m3_public_copy_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit_public_copy(*, spike_path: Path = L1_SPIKE) -> dict[str, Any]:
    from scripts.build_mkm_inter_agent_encoding_status_v1 import _milestone_m3

    if not spike_path.is_file():
        return {"ok": False, "error": "l1_spike_missing", "path": str(spike_path)}
    l1 = json.loads(spike_path.read_text(encoding="utf-8"))
    m3 = _milestone_m3(l1 if isinstance(l1, dict) else None)
    doc = {
        "ok": bool(m3.get("pass")),
        "schema": "mkm_inter_agent_m3_public_copy_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "spike_path": spike_path.relative_to(ROOT).as_posix(),
        "avg_exact_restore_rate": m3.get("avg_exact_restore_rate"),
        "public_copy": m3.get("public_copy_draft"),
        "disclaimer_ko": "무손실 통역·100% 역복원·실전 Lingua Franca 완성을 주장하지 않습니다.",
        "disclaimer_en": "No lossless translation, 100% restore, or production lingua franca completion claim.",
        "boundary_ack": "Public-facing draft lines only; Track A / live trading gates unchanged.",
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spike", type=Path, default=L1_SPIKE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = emit_public_copy(spike_path=args.spike)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
