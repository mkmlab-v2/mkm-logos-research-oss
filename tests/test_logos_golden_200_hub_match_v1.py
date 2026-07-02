"""Golden-200 hub match SSOT — rev21 vs antichrist chapter guard."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rev21_not_antichrist_hub():
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from scripts.logos_golden_200_hub_match_v1 import match_registry_hub_id; "
            "q='요한계시록 21장 새 하늘과 새 땅의 상징은?'; "
            "assert match_registry_hub_id(q, 'rev21_new_creation'); "
            "assert not match_registry_hub_id(q, 'antichrist_666')",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_antichrist_666_hub():
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from scripts.logos_golden_200_hub_match_v1 import match_registry_hub_id; "
            "assert match_registry_hub_id('성경에 666 악마의 숫자, 적그리스도에 대해 궁금해', 'antichrist_666')",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_longtail_gap_hubs_match():
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from scripts.logos_golden_200_hub_match_v1 import match_registry_hub_id; "
            "pairs = ["
            "('이사야 7장 임마누엘 표징은 어떤 맥락에서 읽히는가?', 'isa_immanuel_7'),"
            "('로마서 8장에서 고난과 영광의 연결은 어떻게 서술되는가?', 'romans8_suffering_glory'),"
            "('사도행전 2장 성령 강림은 구약 예언과 어떤 구절로 연결되는가?', 'acts2_pentecost'),"
            "('잠언 8장 지혜의 personification은 창조와 어떻게 연결되는가?', 'proverbs8_wisdom'),"
            "('이사야 53장 고난받는 종의 이미지는 어떤 구절 경로로 읽히는가?', 'isaiah53_suffering_servant'),"
            "('선한 사마리아인 비유는 어떤 이웃 사랑 윤리를 가르치는가?', 'good_samaritan_parable'),"
            "('고린도전서 13장 사랑의 특성은 무엇을 말하는가?', 'corinthians13_love'),"
            "('열왕기 18장 갈멜산에서 엘리야와 바알 선지자의 대결은 어떤 구절로 서술되는가?', 'elijah_carmel'),"
            "]; "
            "assert all(match_registry_hub_id(q, hid) for q, hid in pairs)",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
