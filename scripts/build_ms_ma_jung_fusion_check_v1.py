#!/usr/bin/env python3
"""Fuse MS HWPX filled doc + paste_ready + live readiness into one JSON report."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hwpx import HwpxDocument  # noqa: E402
from hwpx.tools.table_navigation import _collect_document_tables  # noqa: E402
from scripts.fill_hwpx_by_label_cells_v1 import _cell_text  # noqa: E402

DEFAULT_HWPX = ROOT / "reports" / "hwpx_poc" / "ms_microsoft_ma_jung_filled_v1.hwpx"
DEFAULT_DOWNLOADS = Path(
    r"C:\Users\PRO\Downloads\별첨1-2_마중_사업계획서_MKM_공고329.hwpx"
)
PASTE_DIR = ROOT / "reports" / "ms_rq019_paste_ready"
OUT = ROOT / "reports" / "hwpx_poc" / "ms_ma_jung_fusion_check_latest.json"


def _md_hash(path: Path) -> str:
    md = HwpxDocument.open(str(path)).export_markdown()
    return hashlib.sha256(md.encode("utf-8")).hexdigest()[:16]


def _paste_prefix_match(hwpx_path: Path) -> dict[str, bool]:
    doc = HwpxDocument.open(str(hwpx_path))
    idx = _collect_document_tables(doc)

    def cell(ti: int) -> str:
        return _cell_text(idx[ti].table, 0, 0)

    def norm(s: str) -> str:
        return "".join(s.split())[:80]

    pairs = [
        ("k1_T19", "k1_problem_paste.txt", 19),
        ("k2_T23", "k2_method_paste.txt", 23),
        ("k3_T27", "k3_differentiation_paste.txt", 27),
    ]
    out: dict[str, bool] = {}
    for key, fname, ti in pairs:
        paste = (PASTE_DIR / fname).read_text(encoding="utf-8")
        lines = [ln for ln in paste.splitlines() if not ln.startswith("[")]
        p = norm("".join(lines))
        h = norm(cell(ti))
        out[key] = p[:80] == h[:80]
    return out


def _t4_placeholder(hwpx_path: Path) -> dict:
    doc = HwpxDocument.open(str(hwpx_path))
    t4 = _collect_document_tables(doc)[4].table
    zeros = []
    for r in (5, 6, 7):
        v = _cell_text(t4, r, 10)
        if "00백만" in v:
            zeros.append(r)
    return {
        "rows_with_00_col10": zeros,
        "t4_gov_c3": _cell_text(t4, 5, 3),
        "t4_cash_c3": _cell_text(t4, 6, 3),
        "t4_inkind_c3": _cell_text(t4, 7, 3),
        "manual_hancom": "T4 col9–10 합계열: 세 행이 세로 병합이면 한컴에서 200/33/55 또는 병합 해제 후 기입",
    }


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(hwpx: Path, downloads: Path | None) -> dict:
    paste_ready = _load_json(ROOT / "reports" / "ms_rq019_paste_pack_readiness_latest.json")
    outer = _load_json(ROOT / "reports" / "outer_lane_followup_v1.json")
    personadiary = _load_json(ROOT / "reports" / "personadiary_operational_status_latest.json")

    dl_match = None
    if downloads and downloads.is_file():
        dl_match = _md_hash(hwpx) == _md_hash(downloads)

    tracks = {
        "A_hwpx_hancom": {
            "path_repo": str(hwpx),
            "path_downloads": str(downloads) if downloads else None,
            "downloads_same_as_repo": dl_match,
            "open_in_hancom": str(downloads).replace(".hwpx", ".hwp")
            if downloads
            else str(hwpx).replace(".hwpx", ".hwp"),
            "audit_script": "py scripts/audit_ms_ma_jung_hwpx_v1.py --hwpx <path>",
        },
        "B_kstartup_paste": {
            "order": str(PASTE_DIR / "00_paste_order.txt"),
            "assistant": str(ROOT / "reports" / "demo" / "ms_rq019_paste_assistant_v1.html"),
            "paste_pack_ok": paste_ready.get("ok") if paste_ready else None,
            "note": "K-Startup 웹 양식이 별도면 paste 1–7 수동; HWPX 별첨은 A트랙",
        },
    }

    manual = [
        "기업명·주소·인력표 실명·K-Startup 마스킹",
        "T4 합계열(col10) 00백만원 → 한컴에서 200/33/55 (병합 셀 주의)",
        "기술분야 「정보·통신」 등 체크 (T4 r3 c11 후보)",
        "파란 ※ 안내 7곳 삭제(양식 요구 시)",
        "15쪽·표 깨짐 한컴 .hwp 최종 검수",
    ]
    optional = [
        "www.jema12.com/studio CF 규칙 (O-P5 apex는 DONE)",
        "preview.personadiary.com DNS (NXDOMAIN)",
        "K3 GIF 첨부 (MS 본문·HWPX에는 없음 — 의도)",
    ]

    return {
        "schema": "ms_ma_jung_fusion_check_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fact_lock_kpi": "MS Policy A: economy ~49.1% / Jaccard ~0.873 (41658 lexicon SSOT); 3a ~0.890 footnote only; B-track ~47.1% [HYPO]",
        "paste_vs_hwpx_prefix_match": _paste_prefix_match(hwpx),
        "t4": _t4_placeholder(hwpx),
        "tracks": tracks,
        "infra": {
            "paste_pack": paste_ready,
            "outer_lane": outer,
            "personadiary": personadiary,
        },
        "commander_manual": manual,
        "commander_optional": optional,
        "verdict": "READY_HWPX_AND_PASTE_SSOT"
        if all(_paste_prefix_match(hwpx).values())
        else "REVIEW_PASTE_HWPX_DRIFT",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hwpx", type=Path, default=DEFAULT_HWPX)
    ap.add_argument("--downloads", type=Path, default=DEFAULT_DOWNLOADS)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()
    report = build(args.hwpx, args.downloads if args.downloads.is_file() else None)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"out": str(args.out_json), "verdict": report["verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
