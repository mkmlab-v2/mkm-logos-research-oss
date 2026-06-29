#!/usr/bin/env python3
"""Map mkm_deep_research_router_index_v1 → ollama_shallow_router_output_v1 (+ optional handoff)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ollama_shallow_router_nsm_v1 import infer_nsm_prime_tags

HANDOFF = ROOT / "scripts" / "build_ollama_shallow_router_handoff_v1.py"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_research_router_shallow_v1_latest.json"

PLANE_TO_DOMAIN = {
    "research_benchmarks": "devops",
    "research_memory": "oracle",
    "research_edge": "infra",
    "research_meta": "design",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def router_index_to_shallow(router: dict[str, Any]) -> dict[str, Any]:
    plane = str(router.get("research_plane") or "research_meta")
    coords = router.get("coordinates_slkm") if isinstance(router.get("coordinates_slkm"), dict) else {}
    anchors = router.get("anchor_ids") if isinstance(router.get("anchor_ids"), list) else []
    if not anchors:
        source = str(router.get("source_path") or router.get("source_jsonl") or "")
        if source:
            anchors = [source]
    domain = PLANE_TO_DOMAIN.get(plane, "infra")
    return {
        "schema": "ollama_shallow_router_output_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "domain_tag": domain,
        "coordinates": {
            "S": float(coords.get("S", 0.25)),
            "L": float(coords.get("L", 0.25)),
            "K": float(coords.get("K", 0.25)),
            "M": float(coords.get("M", 0.25)),
        },
        "anchor_ids": [str(x).lower() for x in anchors[:3]],
        "nsm_prime_tags": infer_nsm_prime_tags(domain),
        "parse_status": "raw",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Research router index → Ollama shallow router packet")
    parser.add_argument("--input", type=Path, required=True, help="research_router_index JSON")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--with-handoff", action="store_true")
    parser.add_argument("--handoff-out", type=Path, default=ROOT / "reports" / "mkm_research_router_handoff_v1_latest.json")
    args = parser.parse_args()

    router_path = args.input.resolve()
    if not router_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing router index: {router_path}"}), file=sys.stderr)
        return 2

    router = json.loads(router_path.read_text(encoding="utf-8"))
    if router.get("schema") != "mkm_deep_research_router_index_v1":
        print(json.dumps({"ok": False, "error": "input schema must be mkm_deep_research_router_index_v1"}, ensure_ascii=False), file=sys.stderr)
        return 2

    shallow = router_index_to_shallow(router)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(shallow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload: dict[str, Any] = {
        "schema": "mkm_research_router_to_shallow_run_v1",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "shallow_out": _posix_path(args.out),
        "research_plane": router.get("research_plane"),
        "domain_tag": shallow["domain_tag"],
    }

    if args.with_handoff:
        proc = subprocess.run(
            [
                sys.executable,
                str(HANDOFF),
                "--input-json",
                str(args.out),
                "--out-json",
                str(args.handoff_out),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "error": "handoff failed", "stderr": proc.stderr}, ensure_ascii=False), file=sys.stderr)
            return proc.returncode
        payload["handoff_out"] = _posix_path(args.handoff_out)

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
