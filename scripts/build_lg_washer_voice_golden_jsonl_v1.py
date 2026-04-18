# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.88, K:0.45, M:0.72}
# Balance: 93
# Purpose: Export LG washer golden sample records to train/holdout JSONL + split manifest.
# Keywords: LG, washer, golden dataset, jsonl, holdout, PoC
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SRC = ART / "lg_washer_integrity_validation_report_sample_v1.json"
OUT_TRAIN = ART / "lg_washer_voice_golden_train_v1.jsonl"
OUT_HOLDOUT = ART / "lg_washer_voice_golden_holdout_v1.jsonl"
OUT_MANIFEST = ART / "lg_washer_voice_golden_split_manifest_v1.json"

# PoC combinatorial pack: 300 rows, intent histogram (sum=300). Not product-certified speech.
INTENT_TARGETS: dict[str, int] = {
    "SET_COURSE": 50,
    "SET_TEMPERATURE": 38,
    "SET_RINSE_COUNT": 32,
    "SET_SPIN_LEVEL": 34,
    "SET_DURATION": 26,
    "DELAY_START": 26,
    "NOTIFY_WHEN_DONE": 24,
    "QUERY_STATUS": 14,
    "PAUSE_CYCLE": 10,
    "RESUME_CYCLE": 10,
    "STOP_CYCLE": 12,
    "START_CYCLE": 14,
    "CANCEL_OPTION": 10,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _allocate_train_per_intent(counts: dict[str, int], train_total: int, grand_total: int) -> dict[str, int]:
    """Largest-remainder allocation so per-intent train sums to train_total."""
    trains: dict[str, int] = {}
    fractions: list[tuple[float, str]] = []
    acc = 0
    for intent, n in sorted(counts.items()):
        exact = n * train_total / grand_total
        base = int(math.floor(exact))
        trains[intent] = base
        acc += base
        fractions.append((exact - base, intent))
    diff = train_total - acc
    fractions.sort(key=lambda x: x[0], reverse=True)
    idx = 0
    while diff > 0 and fractions:
        _, intent = fractions[idx % len(fractions)]
        cap = counts[intent] - trains[intent]
        if cap > 0:
            trains[intent] += 1
            diff -= 1
        idx += 1
        if idx > grand_total * 2:
            break
    while diff < 0:
        for intent in sorted(trains.keys(), key=lambda k: trains[k], reverse=True):
            if trains[intent] > 0:
                trains[intent] -= 1
                diff += 1
                if diff == 0:
                    break
    return trains


def _synthetic_id(intent: str, seq: int) -> str:
    slug = intent.replace("_", "")
    return f"s300_{slug}_{seq:05d}"


def _gen_set_course(n: int, start_seq: int) -> list[dict[str, Any]]:
    courses = ["표준", "쾌속", "울", "불림", "헹굼만", "탈수만"]
    rows: list[dict[str, Any]] = []
    for i in range(n):
        seq = start_seq + i
        c = courses[i % len(courses)]
        if i % 11 == 10:
            rows.append(
                {
                    "id": _synthetic_id("SET_COURSE", seq),
                    "utterance": "빨리 끝나는 걸로 해줘",
                    "intent": "SET_COURSE",
                    "slots": {},
                    "secondary_intents": [],
                    "expected_action": "reask",
                    "ambiguity_hint": "course_not_specified",
                }
            )
        elif i % 13 == 12:
            rows.append(
                {
                    "id": _synthetic_id("SET_COURSE", seq),
                    "utterance": f"{c} 코스로 90도 돌려줘",
                    "intent": "SET_COURSE",
                    "slots": {"course": c, "temperature_c": 90},
                    "secondary_intents": [],
                    "expected_action": "reask_or_reject",
                    "conflict_hint": "course_temperature_conflict",
                }
            )
        else:
            rows.append(
                {
                    "id": _synthetic_id("SET_COURSE", seq),
                    "utterance": f"{c} 코스로 실행해줘",
                    "intent": "SET_COURSE",
                    "slots": {"course": c},
                    "secondary_intents": ["START_CYCLE"] if i % 4 != 0 else [],
                    "expected_action": "accept",
                }
            )
    return rows


def _gen_set_temperature(n: int, start_seq: int) -> list[dict[str, Any]]:
    temps = [30, 35, 40, 45, 50, 55, 60, 20, 25, 33, 44, 50]
    rows: list[dict[str, Any]] = []
    for i in range(n):
        seq = start_seq + i
        t = temps[i % len(temps)]
        if i % 9 == 8:
            t = 95
            rows.append(
                {
                    "id": _synthetic_id("SET_TEMPERATURE", seq),
                    "utterance": f"온도 {t}도로 맞춰줘",
                    "intent": "SET_TEMPERATURE",
                    "slots": {"temperature_c": t},
                    "secondary_intents": [],
                    "expected_action": "reask_or_reject",
                    "conflict_hint": "temperature_out_of_profile",
                }
            )
        else:
            rows.append(
                {
                    "id": _synthetic_id("SET_TEMPERATURE", seq),
                    "utterance": f"온도 {t}도로 맞춰줘",
                    "intent": "SET_TEMPERATURE",
                    "slots": {"temperature_c": t},
                    "secondary_intents": [],
                    "expected_action": "accept",
                }
            )
    return rows


def _gen_set_rinse(n: int, start_seq: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(n):
        seq = start_seq + i
        rc = (i % 5) + 1
        if i % 10 == 9:
            rc = 10
            rows.append(
                {
                    "id": _synthetic_id("SET_RINSE_COUNT", seq),
                    "utterance": f"헹굼 {rc}회로 해줘",
                    "intent": "SET_RINSE_COUNT",
                    "slots": {"rinse_count": rc},
                    "secondary_intents": [],
                    "expected_action": "reask_or_reject",
                    "conflict_hint": "rinse_out_of_range",
                }
            )
        else:
            rows.append(
                {
                    "id": _synthetic_id("SET_RINSE_COUNT", seq),
                    "utterance": f"헹굼 {rc}회로 해줘",
                    "intent": "SET_RINSE_COUNT",
                    "slots": {"rinse_count": rc},
                    "secondary_intents": [],
                    "expected_action": "accept",
                }
            )
    return rows


def _gen_set_spin(n: int, start_seq: int) -> list[dict[str, Any]]:
    levels = ["약", "중", "강"]
    rows: list[dict[str, Any]] = []
    for i in range(n):
        seq = start_seq + i
        lv = levels[i % 3]
        if i % 12 == 11:
            rows.append(
                {
                    "id": _synthetic_id("SET_SPIN_LEVEL", seq),
                    "utterance": "밤엔 조용히 돌려줘",
                    "intent": "SET_SPIN_LEVEL",
                    "slots": {},
                    "secondary_intents": [],
                    "expected_action": "reask",
                    "ambiguity_hint": "spin_level_not_explicit",
                }
            )
        else:
            rows.append(
                {
                    "id": _synthetic_id("SET_SPIN_LEVEL", seq),
                    "utterance": f"탈수는 {lv}으로 해줘",
                    "intent": "SET_SPIN_LEVEL",
                    "slots": {"spin_level": lv},
                    "secondary_intents": [],
                    "expected_action": "accept",
                }
            )
    return rows


def _gen_set_duration(n: int, start_seq: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(n):
        seq = start_seq + i
        d = 15 + (i * 7 % 200)
        if i % 11 == 10:
            rows.append(
                {
                    "id": _synthetic_id("SET_DURATION", seq),
                    "utterance": "시간은 0분으로 해줘",
                    "intent": "SET_DURATION",
                    "slots": {"duration_min": 0},
                    "secondary_intents": [],
                    "expected_action": "reask_or_reject",
                    "conflict_hint": "duration_out_of_range",
                }
            )
        else:
            rows.append(
                {
                    "id": _synthetic_id("SET_DURATION", seq),
                    "utterance": f"시간 {d}분으로 맞춰줘",
                    "intent": "SET_DURATION",
                    "slots": {"duration_min": d},
                    "secondary_intents": [],
                    "expected_action": "accept",
                }
            )
    return rows


def _gen_delay(n: int, start_seq: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i in range(n):
        seq = start_seq + i
        m = 10 + (i * 13 % 180)
        rows.append(
            {
                "id": _synthetic_id("DELAY_START", seq),
                "utterance": f"{m}분 뒤에 시작해줘",
                "intent": "DELAY_START",
                "slots": {"delay_start_min": m},
                "secondary_intents": [],
                "expected_action": "accept",
            }
        )
    return rows


def _gen_notify(n: int, start_seq: int) -> list[dict[str, Any]]:
    chans = ["app", "tv"]
    rows: list[dict[str, Any]] = []
    for i in range(n):
        seq = start_seq + i
        ch = chans[i % 2]
        if i % 9 == 8:
            rows.append(
                {
                    "id": _synthetic_id("NOTIFY_WHEN_DONE", seq),
                    "utterance": "끝나면 알려줘",
                    "intent": "NOTIFY_WHEN_DONE",
                    "slots": {},
                    "secondary_intents": [],
                    "expected_action": "reask",
                    "ambiguity_hint": "notification_channel_not_specified",
                }
            )
        else:
            rows.append(
                {
                    "id": _synthetic_id("NOTIFY_WHEN_DONE", seq),
                    "utterance": f"끝나면 {ch}로 알려줘",
                    "intent": "NOTIFY_WHEN_DONE",
                    "slots": {"notify_channel": ch},
                    "secondary_intents": [],
                    "expected_action": "accept",
                }
            )
    return rows


def _gen_query(n: int, start_seq: int) -> list[dict[str, Any]]:
    phrases = [
        "지금 상태 알려줘",
        "남은 시간 얼마야",
        "지금 어느 단계야",
        "에러 있어?",
        "문 열어도 돼?",
    ]
    rows: list[dict[str, Any]] = []
    for i in range(n):
        seq = start_seq + i
        rows.append(
            {
                "id": _synthetic_id("QUERY_STATUS", seq),
                "utterance": phrases[i % len(phrases)],
                "intent": "QUERY_STATUS",
                "slots": {},
                "secondary_intents": [],
                "expected_action": "accept",
            }
        )
    return rows


def _gen_pause_resume_stop_start_cancel(
    intent: str, n: int, start_seq: int
) -> list[dict[str, Any]]:
    templates: dict[str, list[str]] = {
        "PAUSE_CYCLE": ["잠깐 멈춰줘", "세탁 멈춰", "일시정지해줘"],
        "RESUME_CYCLE": ["다시 시작해줘", "이어서 돌려줘", "재개해줘"],
        "STOP_CYCLE": ["완전히 멈춰줘", "세탁 종료해줘", "중지해줘"],
        "START_CYCLE": ["지금 시작해줘", "바로 돌려줘", "세탁 시작"],
        "CANCEL_OPTION": ["예약 취소해줘", "지연 시작 취소", "알림만 끄줘"],
    }
    rows: list[dict[str, Any]] = []
    tlist = templates[intent]
    for i in range(n):
        seq = start_seq + i
        utt = tlist[i % len(tlist)]
        slots: dict[str, Any] = {}
        sec: list[str] = []
        if intent == "CANCEL_OPTION" and i % 2 == 0:
            slots = {"cancel_target": "delay_start"}
        if intent == "STOP_CYCLE" and i % 4 == 0:
            sec = ["SET_COURSE"]
            slots = {"course": "쾌속"}
        rows.append(
            {
                "id": _synthetic_id(intent, seq),
                "utterance": utt,
                "intent": intent,
                "slots": slots,
                "secondary_intents": sec,
                "expected_action": "accept",
            }
        )
    return rows


def _build_expanded_records(src: Path) -> list[dict[str, Any]]:
    doc = _load(src)
    seeds = list(doc.get("sample_records") or [])
    if not seeds:
        raise SystemExit("No sample_records in source JSON.")
    seed_counts = Counter(str(r["intent"]) for r in seeds)
    need: dict[str, int] = {}
    for intent, target in INTENT_TARGETS.items():
        need[intent] = max(0, target - seed_counts.get(intent, 0))

    seq_base = 1
    synth_blocks: list[tuple[str, list[dict[str, Any]]]] = [
        ("SET_COURSE", _gen_set_course(need["SET_COURSE"], seq_base)),
    ]
    seq_base += need["SET_COURSE"]
    synth_blocks.append(("SET_TEMPERATURE", _gen_set_temperature(need["SET_TEMPERATURE"], seq_base)))
    seq_base += need["SET_TEMPERATURE"]
    synth_blocks.append(("SET_RINSE_COUNT", _gen_set_rinse(need["SET_RINSE_COUNT"], seq_base)))
    seq_base += need["SET_RINSE_COUNT"]
    synth_blocks.append(("SET_SPIN_LEVEL", _gen_set_spin(need["SET_SPIN_LEVEL"], seq_base)))
    seq_base += need["SET_SPIN_LEVEL"]
    synth_blocks.append(("SET_DURATION", _gen_set_duration(need["SET_DURATION"], seq_base)))
    seq_base += need["SET_DURATION"]
    synth_blocks.append(("DELAY_START", _gen_delay(need["DELAY_START"], seq_base)))
    seq_base += need["DELAY_START"]
    synth_blocks.append(("NOTIFY_WHEN_DONE", _gen_notify(need["NOTIFY_WHEN_DONE"], seq_base)))
    seq_base += need["NOTIFY_WHEN_DONE"]
    synth_blocks.append(("QUERY_STATUS", _gen_query(need["QUERY_STATUS"], seq_base)))
    seq_base += need["QUERY_STATUS"]
    for key in ("PAUSE_CYCLE", "RESUME_CYCLE", "STOP_CYCLE", "START_CYCLE", "CANCEL_OPTION"):
        synth_blocks.append(
            (key, _gen_pause_resume_stop_start_cancel(key, need[key], seq_base))
        )
        seq_base += need[key]

    synth_flat: list[dict[str, Any]] = []
    for _, block in synth_blocks:
        synth_flat.extend(block)

    combined = list(seeds) + synth_flat
    if len(combined) != 300:
        raise SystemExit(f"Expected 300 records, got {len(combined)} (check INTENT_TARGETS vs seeds).")
    return combined


def _stratified_split(
    records: list[dict[str, Any]], train_total: int = 200
) -> tuple[dict[str, str], dict[str, int]]:
    """Assign split train/holdout per intent using largest-remainder allocation."""
    by_intent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_intent[str(r["intent"])].append(r)
    counts = {k: len(v) for k, v in by_intent.items()}
    trains = _allocate_train_per_intent(counts, train_total, len(records))
    split_map: dict[str, str] = {}
    for intent, rows in by_intent.items():
        rows_sorted = sorted(rows, key=lambda x: str(x.get("id")))
        train_n = trains.get(intent, 0)
        for i, r in enumerate(rows_sorted):
            rid = str(r["id"])
            split_map[rid] = "train" if i < train_n else "holdout"
    return split_map, trains


def _run_demo_pack(args: argparse.Namespace) -> int:
    doc = _load(args.src)
    records = list(doc.get("sample_records") or [])
    if not records:
        raise SystemExit("No sample_records in source JSON.")

    train_ids = {r["id"] for r in records[:12]}
    holdout_ids = {r["id"] for r in records[12:]}

    train_rows: list[dict[str, Any]] = []
    holdout_rows: list[dict[str, Any]] = []
    for r in records:
        rid = str(r.get("id"))
        split = "train" if rid in train_ids else "holdout"
        row = {
            "schema": "lg_washer_voice_utterance_v1",
            "split": split,
            "source_report": str(args.src.relative_to(ROOT)).replace("\\", "/"),
            "data_tier": "seed_demo_v1",
            "build_pack": "demo_20_v1",
            **r,
        }
        if split == "train":
            train_rows.append(row)
        else:
            holdout_rows.append(row)

    _write_jsonl(args.train_out, train_rows)
    _write_jsonl(args.holdout_out, holdout_rows)

    manifest = {
        "schema": "lg_washer_voice_golden_split_manifest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "source_report": str(args.src.relative_to(ROOT)).replace("\\", "/"),
        "execution_pack": "docs/final/artifacts/challenge_ax_vertical_lg_hs_execution_pack_v1.json",
        "device_profile_placeholder": "docs/final/artifacts/lg_washer_device_profile_placeholder_v1.json",
        "outputs": {
            "train_jsonl": str(args.train_out.relative_to(ROOT)).replace("\\", "/"),
            "holdout_jsonl": str(args.holdout_out.relative_to(ROOT)).replace("\\", "/"),
        },
        "split_policy": {
            "strategy": "demo_fixed_order_v1",
            "note": "Demo split for 20-sample pack: first 12 train, last 8 holdout.",
            "train_count": len(train_rows),
            "holdout_count": len(holdout_rows),
            "train_ids": [r["id"] for r in train_rows],
            "holdout_ids": [r["id"] for r in holdout_rows],
        },
    }
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.train_out))
    print(str(args.holdout_out))
    print(str(args.manifest_out))
    return 0


def _run_expanded_300(args: argparse.Namespace) -> int:
    records = _build_expanded_records(args.src)
    split_map, trains = _stratified_split(records, train_total=200)
    train_rows: list[dict[str, Any]] = []
    holdout_rows: list[dict[str, Any]] = []
    src_rel = str(args.src.relative_to(ROOT)).replace("\\", "/")
    for r in records:
        rid = str(r["id"])
        split = split_map[rid]
        is_seed = rid.startswith("utt_")
        row = {
            "schema": "lg_washer_voice_utterance_v1",
            "split": split,
            "source_report": src_rel,
            "data_tier": "seed_demo_v1" if is_seed else "synthetic_combinatorial_v1",
            "build_pack": "expanded_300_v1",
            **r,
        }
        if split == "train":
            train_rows.append(row)
        else:
            holdout_rows.append(row)

    train_rows.sort(key=lambda x: str(x["id"]))
    holdout_rows.sort(key=lambda x: str(x["id"]))

    _write_jsonl(args.train_out, train_rows)
    _write_jsonl(args.holdout_out, holdout_rows)

    by_intent_total = Counter(str(r["intent"]) for r in records)
    by_intent_train = Counter(str(r["intent"]) for r in train_rows)
    by_intent_hold = Counter(str(r["intent"]) for r in holdout_rows)

    manifest = {
        "schema": "lg_washer_voice_golden_split_manifest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "source_report": src_rel,
        "execution_pack": "docs/final/artifacts/challenge_ax_vertical_lg_hs_execution_pack_v1.json",
        "device_profile_placeholder": "docs/final/artifacts/lg_washer_device_profile_placeholder_v1.json",
        "outputs": {
            "train_jsonl": str(args.train_out.relative_to(ROOT)).replace("\\", "/"),
            "holdout_jsonl": str(args.holdout_out.relative_to(ROOT)).replace("\\", "/"),
        },
        "split_policy": {
            "strategy": "intent_slot_stratified_v1",
            "note_ko": "의도별로 largest-remainder로 train=200/holdout=100을 배분한 뒤, 의도 내에서는 id 사전순으로 앞쪽을 train에 배정.",
            "train_count": len(train_rows),
            "holdout_count": len(holdout_rows),
            "intent_targets": INTENT_TARGETS,
            "train_allocation_per_intent": trains,
            "counts_total_per_intent": dict(by_intent_total),
            "counts_train_per_intent": dict(by_intent_train),
            "counts_holdout_per_intent": dict(by_intent_hold),
        },
        "data_governance": {
            "data_tier_notes_ko": [
                "utt_*: 샘플 리포트의 시드 20건.",
                "s300_*: PoC 구조 검증용 합성 조합 발화(실제 제품 음성/라벨로 대체 전까지 대외 '실측 골든' 주장 금지).",
            ]
        },
    }
    args.manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.train_out))
    print(str(args.holdout_out))
    print(str(args.manifest_out))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Build LG washer golden JSONL splits from sample report.")
    ap.add_argument("--pack", choices=("demo", "expanded_300"), default="demo", help="demo=20 fixed; expanded_300=seed20+synthetic280 stratified")
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC, help="Source sample report JSON")
    ap.add_argument("--train-out", type=Path, default=OUT_TRAIN)
    ap.add_argument("--holdout-out", type=Path, default=OUT_HOLDOUT)
    ap.add_argument("--manifest-out", type=Path, default=OUT_MANIFEST)
    args = ap.parse_args()

    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    if args.pack == "demo":
        return _run_demo_pack(args)
    return _run_expanded_300(args)


if __name__ == "__main__":
    raise SystemExit(main())
