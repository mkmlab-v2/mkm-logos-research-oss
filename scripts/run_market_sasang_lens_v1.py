#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""시장 사상 렌즈 v1 러너: sasang independent lens JSON → market_sasang_lens_latest.json."""

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

DEFAULT_POLICY = ROOT / "data" / "market_sasang" / "market_sasang_lens_policy_v1.json"
DEFAULT_UPSTREAM = ROOT / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "market_sasang_lens_latest.json"

from scripts.market_sasang_lens_engine_v1 import build_market_sasang_lens_payload, load_policy  # noqa: E402


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit market_sasang_lens_v1 artifact from sasang independent lens JSON.")
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM, help="sasang_independent_lens_latest.json")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    policy = load_policy(args.policy)
    if not args.upstream.is_file():
        print(f"missing upstream lens file: {args.upstream}")
        return 2
    upstream = _read_json(args.upstream)

    payload = build_market_sasang_lens_payload(
        sasang_lens_doc=upstream,
        policy=policy,
        policy_path=str(args.policy.resolve()),
        source_input_path=str(args.upstream.resolve()),
    )
    payload["ts_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
