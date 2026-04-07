#!/usr/bin/env python3
"""Verify expanded showroom feature contracts (week1-4)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List


def verify(html_path: Path) -> List[str]:
    errors: List[str] = []
    content = html_path.read_text(encoding="utf-8")
    required_snippets = [
        'id="trustBadge"',
        "function explainReasonLine(",
        'id="questCard"',
        "function pushReplayEvent(",
        'id="toggleReplayBtn"',
        'id="replaySeek"',
        "function maybeAdvanceReplay(",
        'id="toggleTwinViewBtn"',
        "function setTwinViewCard(",
        "stageState.crisisUntilTs",
    ]
    for snippet in required_snippets:
        if snippet not in content:
            errors.append(f"missing contract: {snippet}")
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description="Verify showroom expansion feature contracts.")
    p.add_argument(
        "--showroom-html",
        default="projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_poll.html",
    )
    ns = p.parse_args()
    html_path = Path(ns.showroom_html)
    if not html_path.is_file():
        print(f"[feature-contract] FAIL\n- missing html: {html_path}")
        return 1
    errors = verify(html_path)
    if errors:
        print("[feature-contract] FAIL")
        for e in errors:
            print(f"- {e}")
        return 1
    print("[feature-contract] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
