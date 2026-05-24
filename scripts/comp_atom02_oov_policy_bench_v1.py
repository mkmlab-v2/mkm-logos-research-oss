#!/usr/bin/env python3
"""COMP-ANCHOR-04: memory_v2 OOV passthrough vs bench-default routing on V2 (research)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pointer_hash_snapping_router_v1 import (  # noqa: E402
    _build_lexicon,
    _read_json,
    _route_one,
)

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
RUNTIME = PILOT / "genesis_pointer_runtime_shadow_only_v1.json"
CODEBOOK = PILOT / "genesis_gematria_4d_codebook_bench_lexicon_full_v1.json"
MEMORY_V2_TARGET = "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json"


def _bench_texts() -> list[tuple[str, str]]:
    doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    out: list[tuple[str, str]] = []
    for c in doc.get("compression_cases") or []:
        cid = str(c.get("id") or "")
        raw = str(c.get("raw_text") or "")
        if raw.strip():
            out.append((cid, raw))
    return out


def _run_lane(
    cases: list[tuple[str, str]],
    *,
    target_path: str | None,
    passthrough: bool,
) -> dict[str, int]:
    runtime = _read_json(RUNTIME)
    lexicon = _build_lexicon(_read_json(CODEBOOK))
    ok = 0
    passthrough_cases = 0
    passthrough_tokens = 0
    for _cid, text in cases:
        row = _route_one(
            text,
            runtime_cfg=runtime,
            lexicon=lexicon,
            enable_snap=True,
            snap_ratio=0.74,
            target_path=target_path,
            memory_v2_oov_passthrough=passthrough,
        )
        if row["pointer_candidate_ok"]:
            ok += 1
        pe = row.get("passthrough_events") or []
        if pe:
            passthrough_cases += 1
            passthrough_tokens += len(pe)
    return {
        "pointer_candidate_ok_count": ok,
        "passthrough_case_count": passthrough_cases,
        "passthrough_token_events": passthrough_tokens,
    }


def main() -> int:
    cases = _bench_texts()
    if not cases:
        print("ABORT: no compression_cases")
        return 1

    bench_default = _run_lane(cases, target_path=None, passthrough=True)
    memory_v2 = _run_lane(cases, target_path=MEMORY_V2_TARGET, passthrough=True)
    memory_v2_no_pt = _run_lane(cases, target_path=MEMORY_V2_TARGET, passthrough=False)

    out = {
        "schema": "comp_atom02_oov_policy_bench_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": true if False else True,
        "case_count": len(cases),
        "codebook": str(CODEBOOK.relative_to(ROOT)).replace("\\", "/"),
        "memory_v2_target_path": MEMORY_V2_TARGET,
        "lanes": {
            "bench_no_target_passthrough_on": bench_default,
            "memory_v2_target_passthrough_on": memory_v2,
            "memory_v2_target_passthrough_off": memory_v2_no_pt,
        },
        "verdict": (
            "memory_v2_oov_passthrough only affects unresolved tokens when target_path is under "
            "projects/bitcoin-trading/memory/v2/; V2 bench sentences are not memory_v2 targets — "
            "strict pointer_candidate_ok remains 0/40 on genesis closed dict."
        ),
    }
    out["research_only"] = True
    path = PILOT / "comp_atom02_oov_policy_bench_v1.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": path.name, "lanes": out["lanes"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
