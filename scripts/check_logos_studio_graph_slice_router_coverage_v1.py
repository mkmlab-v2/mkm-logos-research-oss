#!/usr/bin/env python3
"""Gate: studio embed presets must have router verse_refs present in graph slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from logos_studio_preset_graph_helpers_v1 import verse_node_ids  # noqa: E402
from logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402
from patch_logos_studio_graph_slice_router_verse_stubs_v1 import (  # noqa: E402
    STUDIO_PRESET_ALLOWLIST,
)

DEFAULT_SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_ROUTER = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_router_sidecar_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    args = ap.parse_args()

    graph_doc = json.loads(args.slice_json.read_text(encoding="utf-8-sig"))
    router_doc = json.loads(args.router_json.read_text(encoding="utf-8-sig"))
    presets = router_doc.get("presets") or {}

    failures: list[dict[str, str]] = []
    for preset_id in STUDIO_PRESET_ALLOWLIST:
        block = presets.get(preset_id)
        if not block:
            continue
        rp = block.get("router_path_v1") or block
        refs = [canonical_verse_ref(str(r)) for r in (rp.get("verse_refs") or [])]
        refs = [r for r in refs if r]
        unmapped = [r for r in refs if not verse_node_ids(graph_doc, {r})]
        if unmapped:
            failures.append(
                {
                    "preset_id": preset_id,
                    "reason": "unmapped_verse_refs",
                    "refs": ",".join(unmapped),
                }
            )

    ok = not failures
    print(
        json.dumps(
            {
                "ok": ok,
                "schema": "logos_studio_graph_slice_router_coverage_v1",
                "preset_allowlist": list(STUDIO_PRESET_ALLOWLIST),
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
