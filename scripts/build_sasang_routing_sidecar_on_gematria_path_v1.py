#!/usr/bin/env python3
"""Build sasang routing sidecar for a gematria path (B-track lab; no score fusion)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

DEFAULT_OUT = ROOT / "docs/final/artifacts/sasang_routing_sidecar_on_gematria_path_v1_latest.json"
DEFAULT_FIXTURE = (
    ROOT / "docs/final/artifacts/fixtures/sasang_routing_sidecar_gematria_path_fixture_v1.example.json"
)
SASANG_LENS = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
PRIMITIVE_KERNEL = ROOT / "docs/final/artifacts/sasang_design_primitive_kernel_v1_latest.json"

FORBIDDEN_FLAGS = [
    "no_prophecy_vote_merge",
    "no_score_linear_blend",
    "no_constitutional_quadrant_diagnosis",
    "no_track_a_compression_floor",
]

MUST_NOT_MERGE = [
    "prophecy_vote",
    "track_a_compression_floor",
    "production_gematria_kernel",
    "arm_a_quant_ssot",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pathology_state(heat_proxy: float, kernel: dict[str, Any]) -> str:
    states = (kernel.get("primitives") or {}).get("pathology", {}).get("states") or {}
    if heat_proxy >= float((states.get("crisis") or {}).get("stress_gte", 0.75)):
        return "crisis"
    if heat_proxy >= float((states.get("stress") or {}).get("stress_lt", 0.75)):
        return "stress"
    if heat_proxy >= float((states.get("watch") or {}).get("stress_lt", 0.55)):
        return "watch"
    return "calm"


def _posture_hint(pathology_state: str, direction_score: float) -> tuple[str, str]:
    if pathology_state in ("crisis", "stress"):
        return "entropy_leg_tactical_hold", "tactical"
    if abs(direction_score) < 0.12:
        return "entropy_leg_structural_wait", "structural"
    return "valid_pathway_narrow", "observe"


def build(
    *,
    anchor_ref: str,
    gematria_metadata: dict[str, int],
    recipe_id: str = "gematria_to_4d_bridge",
) -> dict[str, Any]:
    if not SASANG_LENS.is_file():
        raise FileNotFoundError(f"missing sasang lens: {SASANG_LENS}")
    if not PRIMITIVE_KERNEL.is_file():
        raise FileNotFoundError(f"missing primitive kernel: {PRIMITIVE_KERNEL}")

    lens = _load(SASANG_LENS)
    kernel = _load(PRIMITIVE_KERNEL)
    bridge = build_gematria_4d_bridge(gematria_metadata=gematria_metadata)

    stream = lens.get("sasang_stream_outputs") or {}
    machine = stream.get("machine_readables") or {}
    heat_proxy = float(machine.get("heat_proxy", 0.5))
    direction_score = float((lens.get("scores") or {}).get("direction_score", 0.0))
    confidence = float((lens.get("scores") or {}).get("confidence", 0.0))
    pathology = _pathology_state(heat_proxy, kernel)
    posture_hint, entropy_leg = _posture_hint(pathology, direction_score)

    path_id = hashlib.sha256(f"{anchor_ref}|{recipe_id}".encode()).hexdigest()[:16]

    return {
        "schema": "sasang_routing_sidecar_on_gematria_path_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "path_id": path_id,
        "gematria_path_ref": {
            "recipe_id": recipe_id,
            "anchor_ref": anchor_ref,
            "state16": bridge.get("state16"),
            "vector_4d": bridge.get("vector_4d"),
        },
        "sasang_routing_hints": {
            "posture_hint": posture_hint,
            "entropy_leg": entropy_leg,
            "forbidden_flags": list(FORBIDDEN_FLAGS),
            "machine_readables_pointer": f"{SASANG_LENS.as_posix()}#/sasang_stream_outputs/machine_readables",
            "primitive_kernel_ref": PRIMITIVE_KERNEL.as_posix(),
            "pathology_state": pathology,
            "direction_score": direction_score,
            "confidence": confidence,
        },
        "forbidden_synthesis_ack": True,
        "must_not_merge_into": list(MUST_NOT_MERGE),
        "upstream": {
            "sasang_independent_lens": SASANG_LENS.as_posix(),
            "disclaimer_ko": "routing hints only — not clinical constitution · not prophecy vote",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--anchor-ref", type=str, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.fixture.is_file():
        fx = _load(args.fixture)
        anchor_ref = args.anchor_ref or str(fx.get("anchor_ref") or "lab_smoke")
        meta = fx.get("gematria_metadata") or {}
        recipe_id = str(fx.get("recipe_id") or "gematria_to_4d_bridge")
    else:
        anchor_ref = args.anchor_ref or "lab_smoke"
        meta = {"raw_combined_sum": 0, "compressed_combined_sum": 0, "reconstructed_combined_sum": 0}
        recipe_id = "gematria_to_4d_bridge"

    doc = build(anchor_ref=anchor_ref, gematria_metadata={k: int(v) for k, v in meta.items()}, recipe_id=recipe_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "path_id": doc["path_id"], "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
