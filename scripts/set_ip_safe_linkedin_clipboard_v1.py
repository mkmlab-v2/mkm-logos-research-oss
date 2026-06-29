#!/usr/bin/env python3
"""Put IP Safe LinkedIn fix paste body (UTF-8) on Windows clipboard."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Feed top → bottom (newest first). 글 수정 시 이 순서 권장.
FIX_ORDER = [
    "ip_safe_showcase_w4_macro_b2b_ops_en",
    "ip_safe_showcase_w4_macro_b2b_ops_ko",
    "ip_safe_showcase_w3_fact_lock_dual_en",
    "ip_safe_showcase_w3_fact_lock_dual_ko",
    "ip_safe_showcase_w2_topology_radar_en",
    "ip_safe_showcase_w1_compression_governance_en",
    "ip_safe_showcase_w2_topology_radar_ko",
    "ip_safe_showcase_w1_compression_governance_ko",
]

STATE = ROOT / "reports/marketing/.ip_safe_clipboard_state.json"
PASTE_FIX = ROOT / "reports/marketing/ip_safe_paste_fix"
PUBLIC = ROOT / "reports/marketing/linkedin_paste_ready"


def _load_body(item_id: str, *, comment: bool) -> str:
    suffix = "comment" if comment else "post"
    fix = PASTE_FIX / f"{item_id}_{suffix}.txt"
    if fix.is_file():
        return fix.read_text(encoding="utf-8").strip()
    if comment:
        batch = ROOT / "reports/marketing/ip_safe_batch_publish_today_v1.json"
        if batch.is_file():
            for row in json.loads(batch.read_text(encoding="utf-8")):
                if row.get("id") == item_id:
                    return str(row.get("disclaimer") or "").strip()
        raise FileNotFoundError(f"comment not found for {item_id}")
    public = PUBLIC / f"{item_id}_public.txt"
    if public.is_file():
        return public.read_text(encoding="utf-8").strip()
    raise FileNotFoundError(f"paste body not found for {item_id}")


def _set_clipboard(text: str) -> None:
    tmp = ROOT / "reports/marketing/.linkedin_clipboard_tmp.txt"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(text, encoding="utf-8")
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-Content -LiteralPath '{tmp}' -Raw -Encoding UTF8 | Set-Clipboard",
        ],
        check=True,
    )


def _save_state(index: int, item_id: str, *, comment: bool) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(
            {"index": index, "item_id": item_id, "comment": comment, "fix_order": FIX_ORDER},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--item-id", help="Specific queue item id")
    ap.add_argument("--index", type=int, help="FIX_ORDER index (0-based)")
    ap.add_argument("--next", action="store_true", help="Advance from last state index")
    ap.add_argument("--comment", action="store_true", help="Copy disclaimer comment instead of post")
    ap.add_argument("--list", action="store_true", help="Print fix order and exit")
    args = ap.parse_args()

    if args.list:
        for i, iid in enumerate(FIX_ORDER):
            print(f"{i}: {iid}")
        return 0

    index = args.index
    if args.next:
        index = 0
        if STATE.is_file():
            index = int(json.loads(STATE.read_text(encoding="utf-8")).get("index", -1)) + 1
        if index >= len(FIX_ORDER):
            print(json.dumps({"ok": False, "error": "fix_order_complete"}, ensure_ascii=False))
            return 1
    elif args.item_id:
        if args.item_id in FIX_ORDER:
            index = FIX_ORDER.index(args.item_id)
        else:
            index = -1
    elif index is None:
        index = 1  # default: W4 KO (worst Korean mojibake)

    if args.item_id and index < 0:
        item_id = args.item_id
    else:
        if index is None or index < 0 or index >= len(FIX_ORDER):
            print(json.dumps({"ok": False, "error": "invalid_index"}, ensure_ascii=False))
            return 1
        item_id = FIX_ORDER[index]

    body = _load_body(item_id, comment=args.comment)
    _set_clipboard(body)
    if index >= 0:
        _save_state(index, item_id, comment=args.comment)

    label = "comment" if args.comment else "post"
    preview = body[:60].replace("\n", " ")
    print(
        json.dumps(
            {
                "ok": True,
                "item_id": item_id,
                "index": index,
                "kind": label,
                "chars": len(body),
                "preview": preview,
                "next_cmd": "py scripts/set_ip_safe_linkedin_clipboard_v1.py --next",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
