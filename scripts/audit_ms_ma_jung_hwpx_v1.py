#!/usr/bin/env python3
"""Audit MS ma-jung HWPX against Fact-Lock + announcement 329 + budget SSOT."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hwpx import HwpxDocument  # noqa: E402
from hwpx.tools.table_navigation import _collect_document_tables  # noqa: E402
from scripts.fill_hwpx_by_label_cells_v1 import _cell_text  # noqa: E402


def _audit(path: Path) -> dict:
    doc = HwpxDocument.open(str(path))
    md = doc.export_markdown()
    indexed = _collect_document_tables(doc)

    def table(ti: int):
        return indexed[ti].table

    required = [
        "MKM Trust Packet",
        "제2026-329호",
        "[마중]",
        "클라우드 기반 B2B",
        "inter-agent",
        "49.1",
        "0.873",
        "Azure",
        "FinOps",
        "288",
        "200백만",
        "25,000,000",
        "125,000,000",
        "200,000,000",
    ]
    required_ok = {s: s in md for s in required}

    forbidden_hits: list[str] = []
    for pat, label in [
        (r"\b2\.42\b", "2.42"),
        (r"\b71\s*%", "71%"),
        (r"\b46\.7\s*%", "prophecy_46.7"),
        (r"\b50\.1\s*%", "50.1%"),
        (r"예언 적중", "prophecy_hit"),
        (r"mkmlife\.com", "oracle_mkmlife"),
        (r"\[HYPO\]", "hypo_tag"),
        (r"\bTrack A\b", "track_a"),
        (r"\bB-track\b(?!_)", "b_track"),
        (r"\bpytest\b", "pytest"),
        (r"\bexit 0\b", "exit_0"),
        (r"성경", "bible_lens"),
        (r"명리", "myeongni_lens"),
        (r"사상 렌즈", "sasang_lens"),
        (r"근거:\s*중소벵처", "ann_loop"),
        (r"000만원", "placeholder_000"),
        (r"00\.0%", "placeholder_pct"),
        (r"제출 전 마스킹", "masking_guide"),
        (r"MKM-V2-Wire", "internal_task_name"),
        (r"FAIL-COMP", "fail_comp"),
        (r"Seed-Label-Formula", "internal_arch"),
    ]:
        if re.search(pat, md, re.I):
            forbidden_hits.append(label)

    negation_ok = {
        "disclaimer_negation": "주장하지 않습니다" in md,
        "hypo_tag": "[HYPO" in md,
        "no_auto_promote": "자동 승격" in md and "금지" in md,
    }

    t4 = table(4)
    t37 = table(37)
    budget = {
        "t4_gov_c3": _cell_text(t4, 5, 3),
        "t4_cash_c3": _cell_text(t4, 6, 3),
        "t4_inkind_c3": _cell_text(t4, 7, 3),
        "t37_row7_gov": _cell_text(t37, 7, 2),
        "t37_row7_inkind": _cell_text(t37, 7, 3),
        "t37_row7_total": _cell_text(t37, 7, 4),
    }
    budget_ok = (
        "200" in budget["t4_gov_c3"]
        and "33" in budget["t4_cash_c3"]
        and "55" in budget["t4_inkind_c3"]
        and "200,000,000" in budget["t37_row7_gov"]
        and "55,000,000" in budget["t37_row7_inkind"]
    )

    narrative_lens = {}
    for ti, name in [
        (19, "1-1"),
        (20, "1-2"),
        (22, "2-1"),
        (23, "2-2"),
        (27, "3-x"),
    ]:
        t = table(ti)
        text = _cell_text(t, 0, 0)
        narrative_lens[name] = {
            "len": len(text),
            "has_mkm": "MKM" in text or "Trust" in text,
            "has_hint_only": text.strip().startswith("※") and len(text) < 200,
            "snippet": text[:100].replace("\n", " "),
        }

    issues: list[str] = []
    for s, ok in required_ok.items():
        if not ok:
            issues.append(f"missing_required:{s}")
    issues.extend(f"forbidden:{x}" for x in forbidden_hits)
    if not budget_ok:
        issues.append("budget_mismatch")
    for name, info in narrative_lens.items():
        if info["len"] < 100:
            issues.append(f"short_narrative:{name}")
        if info.get("has_hint_only"):
            issues.append(f"hint_only:{name}")

    if md.count("※") > 80:
        issues.append(f"many_hint_blocks:{md.count('※')}")
    if md.count("00백만원") > 3:
        issues.append(f"placeholder_00백만:{md.count('00백만원')}")

    gov_sum = 25 + 125 + 25 + 25  # M won millions in table - actually won
    # verify T37 line gov adds to 200M
    gov_lines = []
    for r in range(2, 7):
        v = _cell_text(t37, r, 2).replace(",", "")
        if v.isdigit():
            gov_lines.append(int(v))
    if sum(gov_lines) != 200_000_000:
        issues.append(f"t37_gov_sum:{sum(gov_lines)}!=200000000")

    t13 = _cell_text(table(13), 0, 0)
    t14 = _cell_text(table(14), 0, 0)
    t15 = _cell_text(table(15), 0, 0)
    t19 = _cell_text(table(19), 0, 0)
    t23 = _cell_text(table(23), 0, 0)
    t27 = _cell_text(table(27), 0, 0)
    dup_checks = {
        "s1_not_prefix_of_1-1": not (len(t19) > 80 and t19[:100] == t13[:100]),
        "s2_not_contains_2-2_opening": not (len(t23) > 80 and t23[:120] in t14),
        "s3_not_contains_3-x_opening": not (len(t27) > 80 and t27[:120] in t15),
        "milestone_block_loop_le_1": md.count(
            "(1) inter-agent Trust Packet·wire 프로파일 동결"
        )
        <= 1,
        "body_has_competitor_table": "경쟁·대안 비교" in t19,
        "body_has_method_spec": "구현·배포 스펙" in t23,
        "body_has_ac_map": "Microsoft AC 산출 매핑" in _cell_text(table(44), 0, 0),
    }
    for k, ok in dup_checks.items():
        if not ok:
            issues.append(f"dup_fail:{k}")

    return {
        "path": path.as_posix(),
        "size_bytes": path.stat().st_size,
        "md_len": len(md),
        "table_count": len(indexed),
        "required_ok": required_ok,
        "negation_ok": negation_ok,
        "budget": budget,
        "budget_ok": budget_ok,
        "t37_gov_line_sum": sum(gov_lines),
        "narrative": narrative_lens,
        "hint_count": md.count("※"),
        "placeholder_00_count": md.count("00백만원"),
        "btrack_471_count": md.count("47.1"),
        "dup_checks": dup_checks,
        "issues": issues,
        "pass": len(issues) == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--hwpx",
        type=Path,
        default=Path(r"C:\Users\PRO\Downloads\별첨1-2_마중_사업계획서_MKM_공고329.hwpx"),
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "reports/hwpx_poc/ms_ma_jung_hwpx_audit_latest.json",
    )
    args = ap.parse_args()
    if not args.hwpx.is_file():
        print(json.dumps({"ok": False, "error": "file_not_found", "path": str(args.hwpx)}))
        return 1
    report = _audit(args.hwpx.resolve())
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
