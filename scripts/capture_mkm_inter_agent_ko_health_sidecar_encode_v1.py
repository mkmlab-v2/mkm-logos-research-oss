#!/usr/bin/env python3
"""M19: Capture baseline vs sidecar-enabled research wire encode (in-process HTTP)."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_encode_v1_latest.json"

HEALTH_SAMPLE = "환자 건강 수면 식사 증상 호흡 피로 회복 체온 임상 바이탈 Silver Tech 모니터링."


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def capture() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    baseline = client.post(
        "/v1/research/mkm_lexicon_wire/encode",
        json={"text": HEALTH_SAMPLE, "zstd_min_raw_bytes": 0},
    )
    sidecar = client.post(
        "/v1/research/mkm_lexicon_wire/encode",
        json={"text": HEALTH_SAMPLE, "zstd_min_raw_bytes": 0, "use_ko_health_sidecar": True},
    )
    b = baseline.json() if baseline.status_code == 200 else {}
    s = sidecar.json() if sidecar.status_code == 200 else {}
    b_n = len(b.get("atom_id_sequence") or [])
    s_n = len(s.get("atom_id_sequence") or [])

    turn = client.post(
        "/v1/research/mkm_inter_agent_wire/turn",
        json={"text": HEALTH_SAMPLE, "turn_id": 1, "use_ko_health_sidecar": True},
    )
    turn_body = turn.json() if turn.status_code == 200 else {}

    return {
        "ok": sidecar.status_code == 200 and s_n > b_n,
        "schema": "mkm_inter_agent_ko_health_sidecar_encode_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "sample_text": HEALTH_SAMPLE,
        "baseline_encode": b,
        "sidecar_encode": s,
        "uplift_atom_count": s_n - b_n,
        "wire_turn_with_sidecar": turn_body,
        "boundary_ack": "Opt-in sidecar on research encode only; not production default.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = capture()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
