#!/usr/bin/env python3
"""Extract normalized KR close snapshot text from raw HTML/text.

Output format is compatible with build_market_pulse_from_close_snapshot_v1.py.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def _strip_tags(raw: str) -> str:
    txt = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.IGNORECASE)
    txt = re.sub(r"<style[\s\S]*?</style>", " ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = html.unescape(txt)
    txt = txt.replace("\xa0", " ")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\s*\n\s*", "\n", txt)
    return txt.strip()


def _extract_number(text: str, pattern: str) -> float | None:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    s = m.group(1).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _first_present(text: str, patterns: list[str]) -> float | None:
    for p in patterns:
        v = _extract_number(text, p)
        if v is not None:
            return v
    return None


def _extract_theme_top3(text: str) -> list[float]:
    vals = re.findall(r"(?:전선|전력설비|광통신|반도체|증권)[^\n]{0,80}?([+-]?\d{1,2}\.\d{1,2})%", text)
    out: list[float] = []
    for v in vals[:3]:
        try:
            out.append(float(v))
        except ValueError:
            continue
    return out


def _build_snapshot_text(
    *,
    foreign: float,
    institution: float,
    up_count: float,
    down_count: float,
    theme_returns_top3: list[float],
) -> str:
    lines = [
        "코스피",
        f"외국인 {foreign:+,.0f} 억원",
        f"기관 {institution:+,.0f} 억원",
        f"상승종목수 {up_count:,.0f}",
        f"하락종목수 {down_count:,.0f}",
        "테마상위",
    ]
    labels = ["전선", "전력설비", "광통신"]
    for idx, r in enumerate(theme_returns_top3[:3]):
        lines.append(f"{labels[idx]} +{r:.2f}%")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract normalized KR close snapshot text from raw input.")
    ap.add_argument("--input", default="", help="Raw html/text input file path.")
    ap.add_argument("--input-url", default="", help="Raw html/text URL (http/https/file).")
    ap.add_argument("--timeout-sec", type=float, default=10.0, help="URL fetch timeout seconds.")
    ap.add_argument("--out-text", required=True, help="Normalized output text file path.")
    ap.add_argument("--out-json", default="", help="Optional parse diagnostics JSON path.")
    ap.add_argument("--source", default="kr_close_snapshot_extractor_v1")
    args = ap.parse_args()

    in_file = str(args.input or "").strip()
    in_url = str(args.input_url or "").strip()
    if bool(in_file) == bool(in_url):
        raise SystemExit("Provide exactly one of --input or --input-url.")

    in_ref = ""
    if in_file:
        in_path = Path(in_file)
        raw = in_path.read_text(encoding="utf-8")
        in_ref = str(in_path)
    else:
        parsed = urlparse(in_url)
        if parsed.scheme not in {"http", "https", "file"}:
            raise SystemExit("input-url scheme must be http/https/file.")
        req = Request(
            in_url,
            headers={"User-Agent": "MKM-MarketPulse-Extractor/1.0"},
        )
        with urlopen(req, timeout=float(args.timeout_sec)) as resp:  # nosec B310
            raw = resp.read().decode("utf-8", errors="replace")
        in_ref = in_url

    text = _strip_tags(raw)

    foreign = _first_present(text, [r"외국인\s*([+-]?[0-9,]+)\s*억원"])
    institution = _first_present(text, [r"기관\s*([+-]?[0-9,]+)\s*억원"])
    up_count = _first_present(text, [r"상승종목수\s*([0-9,]+)"])
    down_count = _first_present(text, [r"하락종목수\s*([0-9,]+)"])
    theme_top3 = _extract_theme_top3(text)

    missing: list[str] = []
    if foreign is None:
        missing.append("foreign")
    if institution is None:
        missing.append("institution")
    if up_count is None:
        missing.append("up_count")
    if down_count is None:
        missing.append("down_count")
    if len(theme_top3) < 3:
        missing.append("theme_top3")
    if missing:
        raise SystemExit(f"missing required fields: {', '.join(missing)}")

    out_text = _build_snapshot_text(
        foreign=foreign,
        institution=institution,
        up_count=up_count,
        down_count=down_count,
        theme_returns_top3=theme_top3,
    )
    out_text_path = Path(args.out_text)
    out_text_path.parent.mkdir(parents=True, exist_ok=True)
    out_text_path.write_text(out_text, encoding="utf-8")

    if args.out_json:
        out_doc = {
            "schema": "kr_market_close_snapshot_extract_v1",
            "source": str(args.source or "kr_close_snapshot_extractor_v1"),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "input": in_ref,
            "output_text": str(out_text_path),
            "foreign_net_buy_krw_eok": foreign,
            "institution_net_buy_krw_eok": institution,
            "up_count": up_count,
            "down_count": down_count,
            "theme_top3_pct": theme_top3[:3],
        }
        out_json_path = Path(args.out_json)
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(str(out_text_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

