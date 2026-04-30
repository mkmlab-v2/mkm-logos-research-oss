#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.5, M:0.5}
# Balance: 90
# Purpose: Update n8n operator onepager live signoff from hold to go.
# Keywords: n8n, signoff, operator, checklist

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ONEPAGER = ROOT / "docs" / "final" / "artifacts" / "n8n_macro_risk_mail_operator_onepager_live_v1.md"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Finalize n8n operator onepager signoff.")
    p.add_argument("--onepager", type=Path, default=DEFAULT_ONEPAGER)
    p.add_argument("--signed-by", type=str, default="MKM Core Team")
    p.add_argument("--status", type=str, choices=["go", "hold"], default="go")
    p.add_argument(
        "--reason",
        type=str,
        default="n8n import/SMTP binding/manual trigger runtime checks completed",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    onepager = args.onepager if args.onepager.is_absolute() else (ROOT / args.onepager)
    text = onepager.read_text(encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _replace(prefix: str, new_line: str, src: str) -> str:
        out_lines = []
        replaced = False
        for line in src.splitlines():
            if line.startswith(prefix):
                out_lines.append(new_line)
                replaced = True
            else:
                out_lines.append(line)
        if not replaced:
            out_lines.append(new_line)
        return "\n".join(out_lines) + "\n"

    text = _replace("- signoff_status:", f"- signoff_status: `{args.status}` (`go` / `hold`)", text)
    text = _replace("- signoff_reason:", f"- signoff_reason: `{args.reason}`", text)
    text = _replace("- signed_by:", f"- signed_by: `{args.signed_by}`", text)
    text = _replace("- signed_at_utc:", f"- signed_at_utc: `{now}`", text)

    onepager.write_text(text, encoding="utf-8")
    print(f"signoff_finalize: PASS -> {onepager}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
