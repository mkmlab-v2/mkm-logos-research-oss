#!/usr/bin/env python3
"""Human-visible B-track Sasang-41k operator board [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/btrack_sasang_41k_operator_board_v1_latest.md"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> str:
    chain = _load(ROOT / "reports/btrack_sasang_41k_hd_chain_v1_latest.json")
    shadow = _load(ROOT / "reports/btrack_sasang_lexicon_shadow_v1_latest.json")
    gate = _load(ROOT / "reports/btrack_sasang_role_mismatch_gate_v1_latest.json")
    completion = _load(ROOT / "reports/btrack_sasang_41k_completion_gate_v1_latest.json")
    hot = _load(ROOT / "reports/btrack_sasang_41k_hot_reload_v1_latest.json")
    psi_bridge = _load(ROOT / "reports/btrack_sasang_psi_role_bridge_v1_latest.json")

    role_counts = shadow.get("role_counts") or {}
    mismatch = shadow.get("mismatch_summary") or {}

    lines = [
        "# B-track Sasang-41k — HD Operator Board",
        "",
        "> **codebook 본체 비변경** · shadow sidecar only · Track B `[HYPO]`",
        "",
        f"생성: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        "",
        "## 한눈 요약",
        "",
        "| 항목 | 값 |",
        "|------|-----|",
        f"| HD chain ok | **{chain.get('ok')}** |",
        f"| hot-reload ok | **{hot.get('ok')}** |",
        f"| psi bridge ok | **{psi_bridge.get('bridge_ok')}** |",
        f"| completion score | **{completion.get('completion_score')}** |",
        f"| completion pass | **{completion.get('completion_pass')}** |",
        f"| lexicon shadow rows | **{shadow.get('codebook_entry_count')}** |",
        f"| codebook unmodified | **{shadow.get('codebook_unmodified')}** |",
        f"| mismatch rate | **{mismatch.get('mismatch_rate')}** |",
        f"| mismatch gate | **{(gate.get('summary') or {}).get('gate_pass')}** |",
        f"| track_a_bridge | **{shadow.get('track_a_bridge')}** |",
        "",
        "## 4AI 역할 분포 (lexicon shadow)",
        "",
        "| role | count | ops semantic |",
        "|------|------:|--------------|",
    ]
    semantics = {
        "taeyang": "scale_out_expansion",
        "taeeum": "persistence_archive",
        "soyang": "execution_transition",
        "soeumin": "stability_cooling",
    }
    for role in ("taeyang", "taeeum", "soyang", "soeumin"):
        lines.append(f"| {role} | {role_counts.get(role, 0)} | {semantics[role]} |")

    lines.extend(
        [
            "",
            "## 열 파일",
            "",
            "1. `reports/btrack_sasang_41k_auto_continue_v1_latest.json`",
            "2. `reports/btrack_sasang_41k_hot_reload_v1_latest.json`",
            "3. `reports/btrack_sasang_psi_role_bridge_v1_latest.json`",
            "4. `reports/btrack_sasang_lexicon_shadow_v1_latest.json`",
            "5. `reports/btrack_sasang_41k_completion_gate_v1_latest.json`",
            "",
            "## 재현",
            "",
            "```powershell",
            "py scripts/run_btrack_sasang_41k_auto_continue_v1.py --verbose",
            "```",
            "",
            "## 격벽",
            "",
            "- MS 헤드라인·B2B 카피에 사상/게마트리아 **직접 주입 금지**",
            "- master codebook **쓰기 금지** — shadow만",
            "- Final Action·Track A 승격 **아님**",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build(), encoding="utf-8")
    print(str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
