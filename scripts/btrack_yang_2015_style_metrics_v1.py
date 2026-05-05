#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B-track: Yang(2015)-style surface eight-char counts (elements, yin/yang, six-god buckets).

Uses four pillar strings (gan+ji each) only. Branch 십성 uses 地支本气天干 (main qi stem) per
traditional table — deterministic, not subjective.

NOT peer review replication: calendar boundary vs Yang's commercial calendar may still differ.
See: data/myeongni/paper_contract_maps/yang_2015_four_pillars_personality_map_v1.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "commander_myeongni_lens_latest.json"
DEFAULT_OUT = ROOT / "reports" / "btrack_yang_2015_style_metrics_latest.json"

STEMS_ORDER = "甲乙丙丁戊己庚辛壬癸"
STEMS_KO_ORDER = "갑을병정무기경신임계"

_GAN_KO_TO_EL: dict[str, str] = {
    "갑": "wood",
    "을": "wood",
    "병": "fire",
    "정": "fire",
    "무": "earth",
    "기": "earth",
    "경": "metal",
    "신": "metal",
    "임": "water",
    "계": "water",
}
_GAN_ZH = "甲乙丙丁戊己庚辛壬癸"
_ORDER_EL = ("wood", "wood", "fire", "fire", "earth", "earth", "metal", "metal", "water", "water")
_GAN_ZH_TO_EL = {_GAN_ZH[i]: _ORDER_EL[i] for i in range(10)}
GAN_TO_ELEMENT: dict[str, str] = {**_GAN_KO_TO_EL, **_GAN_ZH_TO_EL}

# 地支本气 (天干) — 십성 비교용 (한글·한자 병기)
_BRANCH_MAIN_GAN_KO: dict[str, str] = {
    "자": "계",
    "축": "기",
    "인": "갑",
    "묘": "을",
    "진": "무",
    "사": "병",
    "오": "정",
    "미": "기",
    "신": "경",
    "유": "신",
    "술": "무",
    "해": "임",
}
_BRANCH_MAIN_GAN_ZH = "子丑寅卯辰巳午未申酉戌亥"
_BRANCH_ZH_TO_KO = dict(zip(_BRANCH_MAIN_GAN_ZH, _BRANCH_MAIN_GAN_KO.keys()))
BRANCH_MAIN_GAN: dict[str, str] = {
    **_BRANCH_MAIN_GAN_KO,
    **{zh: _BRANCH_MAIN_GAN_KO[_BRANCH_ZH_TO_KO[zh]] for zh in _BRANCH_MAIN_GAN_ZH},
}

ZHI_YANG = frozenset({"자", "인", "진", "오", "신", "술"}) | frozenset({"子", "寅", "辰", "午", "申", "戌"})


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pillar_gan_ji(pillar: str) -> tuple[str, str]:
    s = str(pillar).strip()
    if len(s) >= 2:
        return s[0], s[1]
    return "", ""


def _gan_yinyang(gan: str) -> str:
    if gan in STEMS_ORDER:
        i = STEMS_ORDER.index(gan)
    elif gan in STEMS_KO_ORDER:
        i = STEMS_KO_ORDER.index(gan)
    else:
        return ""
    return "yang" if i % 2 == 0 else "yin"


def _zhi_yinyang(ji: str) -> str:
    return "yang" if ji in ZHI_YANG else "yin"


def _six_god_bucket(day_gan: str, target_gan: str) -> str:
    """Return officer|resource|parallel|hurting_god|wealth for day master vs target stem."""
    if not day_gan or not target_gan:
        return "unknown"
    d_el = GAN_TO_ELEMENT.get(day_gan)
    t_el = GAN_TO_ELEMENT.get(target_gan)
    if not d_el or not t_el:
        return "unknown"
    order = ["wood", "fire", "earth", "metal", "water"]

    def idx(e: str) -> int:
        return order.index(e)

    di, ti = idx(d_el), idx(t_el)
    if d_el == t_el:
        return "parallel"
    if (di + 1) % 5 == ti:
        return "hurting_god"
    if (ti + 1) % 5 == di:
        return "resource"
    if (di + 2) % 5 == ti or (di - 3) % 5 == ti:
        return "wealth"
    if (ti + 2) % 5 == di or (ti - 3) % 5 == di:
        return "officer"
    return "unknown"


def extract_pillars_from_commander(doc: dict[str, Any]) -> dict[str, str]:
    adv = doc.get("advanced") if isinstance(doc.get("advanced"), dict) else {}
    ins = adv.get("input_summary") if isinstance(adv.get("input_summary"), dict) else {}
    pillars = ins.get("pillars") if isinstance(ins.get("pillars"), dict) else {}
    if not pillars or not any(str(v).strip() for v in pillars.values()):
        slots = adv.get("slots") if isinstance(adv.get("slots"), dict) else {}
        sp = slots.get("pillars") if isinstance(slots.get("pillars"), dict) else {}
        if sp:
            pillars = sp
    return {k: str(pillars.get(k, "") or "") for k in ("year", "month", "day", "hour")}


def compute_yang_style_metrics(pillars: dict[str, str]) -> dict[str, Any]:
    """Surface 8-char element counts, yin/yang counts, six-god buckets vs day stem."""
    order_keys = ("year", "month", "day", "hour")
    chars: list[tuple[str, str, str]] = []  # (role, gan|ji, char)
    for pk in order_keys:
        p = str(pillars.get(pk, "") or "")
        gan, ji = _pillar_gan_ji(p)
        if gan:
            chars.append((f"{pk}_stem", "gan", gan))
        if ji:
            chars.append((f"{pk}_branch", "ji", ji))

    element_counts: dict[str, int] = {"wood": 0, "fire": 0, "earth": 0, "metal": 0, "water": 0}
    yinyang_counts = {"yang": 0, "yin": 0}
    for role, typ, ch in chars:
        if typ == "gan":
            el = GAN_TO_ELEMENT.get(ch)
            yy = _gan_yinyang(ch)
        else:
            main = BRANCH_MAIN_GAN.get(ch, "")
            el = GAN_TO_ELEMENT.get(main)
            yy = _zhi_yinyang(ch)
        if el and el in element_counts:
            element_counts[el] += 1
        if yy in yinyang_counts:
            yinyang_counts[yy] += 1

    day_gan, day_ji = _pillar_gan_ji(str(pillars.get("day", "") or ""))
    six_buckets = {"officer": 0, "resource": 0, "parallel": 0, "hurting_god": 0, "wealth": 0}
    six_detail: list[dict[str, str]] = []
    if day_gan:
        for role, typ, ch in chars:
            if role == "day_stem":
                continue
            tgt = ch if typ == "gan" else BRANCH_MAIN_GAN.get(ch, "")
            if not tgt:
                continue
            b = _six_god_bucket(day_gan, tgt)
            if b in six_buckets:
                six_buckets[b] += 1
            six_detail.append(
                {
                    "position": role,
                    "surface": ch,
                    "target_stem_for_ten_god": tgt,
                    "bucket": b,
                }
            )

    return {
        "schema": "btrack_yang_2015_style_metrics_v1",
        "version": "1.0.0",
        "contract": "surface_eight_char_counts_plus_six_god_buckets_v1",
        "pillars": {k: str(pillars.get(k, "") or "") for k in order_keys},
        "day_stem": day_gan,
        "day_stem_yinyang": _gan_yinyang(day_gan) if day_gan else "",
        "element_counts_surface_8": element_counts,
        "yinyang_counts_surface_8": yinyang_counts,
        "six_god_buckets_yang2015_names": six_buckets,
        "six_god_detail": six_detail,
        "branch_main_gan_note": "Branches mapped to 본기天干 per BRANCH_MAIN_GAN for 십성 vs 일간.",
        "day_branch_for_audit": day_ji,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = _read_json(args.input)
    pillars = extract_pillars_from_commander(doc)
    body = compute_yang_style_metrics(pillars)
    out = {
        **body,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(args.input.resolve()),
        "b_track_notice": "[MKM-B-TRACK] Yang-style counts for research; not A-track; not clinical.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
