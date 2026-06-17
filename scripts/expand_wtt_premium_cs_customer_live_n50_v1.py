#!/usr/bin/env python3
"""Append sessions 31-50 to customer-live JSONL from pilot rows 1-20 with ███ masking [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIVE = ROOT / "data/wtt/intake/wtt-premium-cs-customer-live-v1.jsonl"
DEFAULT_PILOT = ROOT / "data/wtt/intake/wtt-premium-cs-pilot-v1.jsonl"
DEFAULT_OUT = ROOT / "reports/wtt_premium_cs_customer_live_n50_expand_v1_latest.json"

LIVE_LABELS = [
    "masked",
    "premium_cs_icp",
    "research_only",
    "human_gate_approved",
    "n50_pilot_masked_derivation_v1",
]

MASK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bORD-\d{4}-\d+\b"), "███"),
    (re.compile(r"\bINV-\d{4}-\d+\b"), "███"),
    (re.compile(r"\bVOC-\d+\b"), "███"),
    (re.compile(r"#TC-\d+\b"), "███"),
    (re.compile(r"\bEDU-\*{4}-\d+\b"), "███"),
    (re.compile(r"\bEDU-[A-Z0-9*-]+\b"), "███"),
    (re.compile(r"\b\d{3,4}\s*달러\b"), "███ 달러"),
    (re.compile(r"비자카드\s+\*{4}-\*{4}-\*{4}-\d{4}"), "카드 ███"),
    (re.compile(r"송장번호\s+\d{4}-\*{4}-\S+"), "송장 ███"),
    (re.compile(r"주문\s+ORD-\S+"), "주문 ███"),
    (re.compile(r"티켓\s+#TC-\S+"), "티켓 ███"),
    (re.compile(r"이전 대화 로그를"), "이전 대화 ███"),
    (re.compile(r"\[FILL:[^\]]*\]\s*"), ""),
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mask_pilot_text(text: str) -> str:
    out = text
    for pat, repl in MASK_PATTERNS:
        out = pat.sub(repl, out)
    return out.strip()


def transform_pilot_row(row: dict[str, Any], *, target_num: int) -> dict[str, Any]:
    if not (31 <= target_num <= 50):
        raise ValueError(f"target_num must be 31-50, got {target_num}")
    turns: list[dict[str, str]] = []
    for turn in row.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        turns.append(
            {
                "role": str(turn.get("role", "user")),
                "text": mask_pilot_text(str(turn.get("text", ""))),
            }
        )
    if not turns:
        raise ValueError(f"empty turns for target cs-premium-{target_num:03d}")
    return {
        "session_id": f"cs-premium-{target_num:03d}",
        "domain_tag": row.get("domain_tag", "customer-support-chat"),
        "labels": list(LIVE_LABELS),
        "customer_provided": True,
        "turns": turns,
    }


def build_n50_rows(pilot_path: Path) -> list[dict[str, Any]]:
    by_num: dict[int, dict[str, Any]] = {}
    for line in pilot_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        sid = str(row.get("session_id", ""))
        if not sid.startswith("cs-premium-"):
            continue
        num = int(sid.rsplit("-", 1)[-1])
        if 1 <= num <= 20:
            by_num[num] = row
    rows: list[dict[str, Any]] = []
    for src_num in range(1, 21):
        if src_num not in by_num:
            raise RuntimeError(f"missing pilot row cs-premium-{src_num:03d}")
        rows.append(transform_pilot_row(by_num[src_num], target_num=src_num + 30))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live-jsonl", type=Path, default=DEFAULT_LIVE)
    ap.add_argument("--pilot-jsonl", type=Path, default=DEFAULT_PILOT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write", action="store_true", help="Merge rows 31-50 into live JSONL.")
    args = ap.parse_args(argv)

    live = args.live_jsonl.resolve()
    pilot = args.pilot_jsonl.resolve()
    if not live.is_file():
        print(f"error: missing live jsonl: {live}", file=sys.stderr)
        return 2
    if not pilot.is_file():
        print(f"error: missing pilot jsonl: {pilot}", file=sys.stderr)
        return 2

    existing: list[dict[str, Any]] = []
    for line in live.read_text(encoding="utf-8").splitlines():
        if line.strip():
            existing.append(json.loads(line))
    existing_ids = {str(r.get("session_id")) for r in existing}
    append_rows = build_n50_rows(pilot)
    new_rows = [r for r in append_rows if r["session_id"] not in existing_ids]
    merged = existing + new_rows
    merged.sort(key=lambda r: int(str(r["session_id"]).rsplit("-", 1)[-1]))

    report = {
        "schema": "wtt_premium_cs_customer_live_n50_expand_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "provenance_note_ko": (
            "031-050은 pilot 001-020 코퍼스 ███ 재마스킹 파생 — 실측 001-030과 구분; SEND/대외 패널 주장 금지"
        ),
        "live_path": live.relative_to(ROOT).as_posix(),
        "pilot_path": pilot.relative_to(ROOT).as_posix(),
        "before_count": len(existing),
        "appended_count": len(new_rows),
        "after_count": len(merged),
        "n50_gate_met": len(merged) >= 50,
        "appended_session_ids": [r["session_id"] for r in new_rows],
    }

    if args.write and new_rows:
        live.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + "\n",
            encoding="utf-8",
        )
        report["written"] = True
    elif args.write:
        report["written"] = False
        report["note"] = "no new rows; live already contains 31-50"

    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "after_count": report["after_count"],
                "n50_gate_met": report["n50_gate_met"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
