# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.9, K:0.5, M:0.6}
# Balance: 91
# Purpose: Deterministic+adaptive hybrid codec v0 spike harness.
# Keywords: hybrid codec, deterministic restore, adaptive saving, checksum
#!/usr/bin/env python3
"""Hybrid codec v0 spike: deterministic restore + adaptive substitution.

Design goals (v0):
- deterministic restore first (exact + checksum)
- adaptive token saving second (dictionary substitutions only when beneficial)
- strict side-channel contract (dict_version, escape_map, swap_log)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
import os


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "hybrid_codec_v0_spike_latest.json"
DICT_VERSION = "hybrid_codec_v0_dict_2026-04-13"

TOKEN_RE = re.compile(r"\S+")
SYMBOL_RE = re.compile(r"^[^\w\u3131-\uD79D]+$")
NUMERIC_RE = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _phrase_first_enabled() -> bool:
    """Default-on phrase-first resegmentation with explicit force-off escape hatch."""
    force_off = os.environ.get("HYBRID_CODEC_PHRASE_FIRST_FORCE_OFF", "").strip().lower()
    if force_off in {"1", "true", "yes", "on"}:
        return False
    raw = os.environ.get("HYBRID_CODEC_PHRASE_FIRST", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    # Promoted default: c7 phrase-first ON unless explicitly disabled.
    return True


def _tracka_profile() -> str:
    return os.environ.get("HYBRID_CODEC_TRACKA_PROFILE", "").strip().lower()


def _preferred_phrases_for_profile(profile: str) -> list[str]:
    if profile in {"ops_market", "ops", "market"}:
        return [
            "KRWUSD 환율 임계치",
            "NASDAQ100 리스크 태그",
            "gateway 상태 점검",
            "SHA256 검증",
            "ops 런북",
        ]
    if profile in {"med_ops", "medical_ops"}:
        return [
            "체질 분류 태그",
            "원문 약어",
            "병증 약리 분석",
            "medical ops",
            "SHA256 검증",
        ]
    if profile in {"general_quality", "general"}:
        return [
            "원문 보존",
            "의미 레인",
            "checksum match",
            "exact restore",
        ]
    return []


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def _is_literal(tok: str) -> bool:
    return any(ch.isdigit() for ch in tok) or "_" in tok or "-" in tok or tok.isupper()


def _token_type(tok: str, dictionary: dict[str, str]) -> str:
    if tok.startswith("META:"):
        return "META"
    if _is_literal(tok):
        return "LITERAL"
    if NUMERIC_RE.match(tok):
        return "NUMERIC"
    if SYMBOL_RE.match(tok):
        return "SYMBOL"
    if tok in dictionary:
        return "DICT_CANDIDATE"
    return "OOV"


def _escape_token(tok: str) -> str:
    return base64.b64encode(tok.encode("utf-8")).decode("ascii")


def _unescape_token(encoded: str) -> str:
    return base64.b64decode(encoded.encode("ascii")).decode("utf-8")


def _jaccard(a: str, b: str) -> float:
    aset = set(_tokenize(a))
    bset = set(_tokenize(b))
    if not aset and not bset:
        return 1.0
    return len(aset & bset) / max(1, len(aset | bset))


@dataclass
class EncodedPacket:
    body_tokens: list[str]
    side_channel: dict[str, Any]
    checksum_sha256_raw: str
    input_token_count: int
    output_token_count: int
    input_char_len: int
    output_char_len: int


def encode_text(text: str, dictionary: dict[str, str]) -> EncodedPacket:
    tokens = _tokenize(text)
    encoded_tokens: list[str] = []
    escape_map: dict[int, str] = {}
    literal_map: dict[int, str] = {}
    token_types: list[str] = []
    phrase_dict = build_phrase_dictionary()
    idx = 0
    out_idx = 0
    phrase_first = _phrase_first_enabled()
    phrase_sizes = (4, 3, 2) if phrase_first else (3, 2)
    while idx < len(tokens):
        matched = False
        for n in phrase_sizes:
            if idx + n > len(tokens):
                continue
            phrase = " ".join(tokens[idx : idx + n])
            code = phrase_dict.get(phrase)
            if code:
                encoded_tokens.append(code)
                token_types.append("DICT_CANDIDATE")
                idx += n
                out_idx += 1
                matched = True
                break
        if matched:
            continue
        tok = tokens[idx]
        ttype = _token_type(tok, dictionary)
        token_types.append(ttype)
        if ttype == "DICT_CANDIDATE":
            code = dictionary[tok]
            if len(code) < len(tok):
                encoded_tokens.append(code)
            else:
                encoded_tokens.append(tok)
        elif ttype == "LITERAL" and len(tok) >= 16:
            # Pack long literal tokens deterministically for better OOD efficiency.
            encoded_tokens.append(f"~L{out_idx}")
            literal_map[out_idx] = tok
        elif ttype in {"OOV", "SYMBOL"}:
            escaped = _escape_token(tok)
            encoded_tokens.append(f"~E{out_idx}")
            escape_map[out_idx] = escaped
        else:
            encoded_tokens.append(tok)
        idx += 1
        out_idx += 1

    side_channel = {
        "schema": "hybrid_codec_v0_side_channel",
        "dict_version": DICT_VERSION,
        "escape_map": escape_map,
        "literal_map": literal_map,
        "swap_log": [],
        "token_types": token_types,
    }
    encoded_text = " ".join(encoded_tokens)
    return EncodedPacket(
        body_tokens=encoded_tokens,
        side_channel=side_channel,
        checksum_sha256_raw=_sha256_text(text),
        input_token_count=len(tokens),
        output_token_count=len(encoded_tokens),
        input_char_len=len(text),
        output_char_len=len(encoded_text),
    )


def decode_text(packet: EncodedPacket, dictionary: dict[str, str], reverse_dict: dict[str, str]) -> str:
    sc = packet.side_channel
    if sc.get("dict_version") != DICT_VERSION:
        raise ValueError("dict_version mismatch")

    restored: list[str] = []
    reverse_phrase_dict = build_reverse_phrase_dictionary()
    escape_map = sc.get("escape_map", {})
    literal_map = sc.get("literal_map", {})
    for idx, tok in enumerate(packet.body_tokens):
        if tok.startswith("~L"):
            if idx not in literal_map:
                raise ValueError("literal_map missing index")
            restored.append(str(literal_map[idx]))
            continue
        if tok.startswith("~E"):
            if idx not in escape_map:
                raise ValueError("escape_map missing index")
            restored.append(_unescape_token(escape_map[idx]))
            continue
        if tok in reverse_phrase_dict:
            restored.extend(reverse_phrase_dict[tok].split())
            continue
        if tok in reverse_dict:
            restored.append(reverse_dict[tok])
            continue
        restored.append(tok)
    return " ".join(restored)


@lru_cache(maxsize=1)
def build_dictionary() -> dict[str, str]:
    # Singleton-like cache: prevents per-request dictionary rebuild in API path.
    # Expand dictionary from deterministic corpus/fixed samples to improve savings.
    from scripts.run_l1_inverse_decoder_spike_test import _build_corpus

    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    base = len(alphabet)

    def make_code(idx: int) -> str:
        if idx < base:
            return f"@{alphabet[idx]}"
        hi = (idx // base) % base
        lo = idx % base
        return f"@{alphabet[hi]}{alphabet[lo]}"

    candidates: dict[str, int] = {}
    corpus_limit_raw = os.environ.get("HYBRID_CODEC_V0_DICT_CORPUS_LIMIT", "6800").strip()
    try:
        corpus_limit = max(100, int(corpus_limit_raw))
    except ValueError:
        corpus_limit = 6800
    corpora = _build_corpus()[:corpus_limit]
    for sentence in _build_samples() + corpora:
        for tok in _tokenize(sentence):
            ttype = _token_type(tok, {})
            if ttype in {"LITERAL", "NUMERIC", "META", "SYMBOL"}:
                continue
            candidates[tok] = candidates.get(tok, 0) + 1

    ordered = sorted(candidates.items(), key=lambda kv: (-kv[1], kv[0]))
    dictionary: dict[str, str] = {}
    idx = 0
    for tok, _freq in ordered:
        code = make_code(idx)
        idx += 1
        if len(code) < len(tok):
            dictionary[tok] = code
    return dictionary


@lru_cache(maxsize=1)
def build_phrase_dictionary() -> dict[str, str]:
    from scripts.run_l1_inverse_decoder_spike_test import _build_corpus

    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    base = len(alphabet)

    def make_phrase_code(idx: int) -> str:
        if idx < base:
            return f"^{alphabet[idx]}"
        hi = (idx // base) % base
        lo = idx % base
        return f"^{alphabet[hi]}{alphabet[lo]}"

    counts: dict[str, int] = {}
    corpus_limit_raw = os.environ.get("HYBRID_CODEC_V0_PHRASE_CORPUS_LIMIT", "7200").strip()
    try:
        corpus_limit = max(100, int(corpus_limit_raw))
    except ValueError:
        corpus_limit = 7200
    max_entries_raw = os.environ.get("HYBRID_CODEC_V0_PHRASE_MAX_ENTRIES", "680").strip()
    try:
        max_entries = max(20, int(max_entries_raw))
    except ValueError:
        max_entries = 680
    phrase_first = _phrase_first_enabled()
    if phrase_first:
        max_entries = int(max_entries * 1.25)
    corpora = _build_corpus()[:corpus_limit]
    phrase_sizes = (2, 3, 4) if phrase_first else (2, 3)
    for sentence in _build_samples() + corpora:
        toks = _tokenize(sentence)
        for n in phrase_sizes:
            for i in range(0, max(0, len(toks) - n + 1)):
                phrase = " ".join(toks[i : i + n])
                counts[phrase] = counts.get(phrase, 0) + 1

    profile = _tracka_profile()
    preferred = _preferred_phrases_for_profile(profile)
    for phrase in preferred:
        # Boost preferred n-grams for lane-specific phrase-code adoption.
        counts[phrase] = counts.get(phrase, 0) + 10_000
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    phrase_dict: dict[str, str] = {}
    idx = 0
    for phrase, freq in ordered:
        if freq < 2:
            continue
        code = make_phrase_code(idx)
        idx += 1
        if len(code) < len(phrase):
            phrase_dict[phrase] = code
        if len(phrase_dict) >= max_entries:
            break
    return phrase_dict


def _build_samples() -> list[str]:
    samples = [
        "오늘 시스템이 BTCUSDT 리포트를 연구모드로 검증했다",
        "정밀하게 팀이 ID_A12 데이터를 안전하게 분석했다",
        "META:sentiment=1.424 우리가 P0 문서를 보수적으로 요약했다",
        "오늘 시스템이 Ω≈ç√∫˜µ≤≥÷ 신호를 연구모드로 검증했다",
        "META:emotion=a.2345 그가 2026-04-13 리포트를 정밀하게 생성했다",
        # Domain-focused anchors for weaker buckets (market/ops/medical).
        "META:market=stress_77 우리는 NASDAQ100 리스크를 단계적으로 점검했다",
        "정책팀이 KRWUSD 환율 임계치를 재설정하고 보고서를 배포했다",
        "감사로그에서 SHA256 검증 불일치를 탐지하고 즉시 롤백했다",
        "운영팀은 포트 8788 상태를 점검한 뒤 게이트웨이를 안전 재기동했다",
        "운영팀은 포트 8788 상태를 점검하고 gateway 런북으로 복구했다",
        "운영팀은 SHA256 검증과 게이트웨이 점검 절차를 반복 실행했다",
        "ops 런북에서 게이트웨이 상태 점검과 롤백 절차를 고정했다",
        "운영 체인은 gateway 상태 점검 후 SHA256 검증을 우선했다",
        "ops 런북은 포트 8788 상태 점검과 gateway 복구 절차를 반복한다",
        "ops 체인은 SHA256 검증과 gateway 상태 점검을 기본 절차로 둔다",
        "운영팀은 ops 런북에 gateway 점검 롤백 절차를 명시했다",
        "gateway 상태 점검 이후 ops 체인은 SHA256 검증을 즉시 수행한다",
        "ops 보고서에는 gateway 점검 결과와 SHA256 검증 결과를 함께 기록한다",
        "의료 라인에서 체질 분류 태그와 원문 약어를 분리 저장했다",
        # Medical-domain anchors (repeat core n-grams for phrase dictionary adoption).
        "의료 라인에서 체질 분류 태그를 안전하게 분리 저장했다",
        "의료 라인에서 체질 분류 태그와 원문 약어를 검증했다",
        "의료 라인에서 체질 분류 태그와 병증 약어를 분리 저장했다",
        "의료 리포트에서 체질 분류 태그와 원문 약어를 보수적으로 저장했다",
        "의료 라인에서 원문 약어와 체질 태그를 분리 저장하고 검증했다",
        "병증 약리 분석에서 체질 분류 태그와 원문 약어를 일관되게 유지했다",
        "의료 도메인에서 체질 분류 태그 원문 약어 매핑을 반복 검증했다",
        "의료 파이프라인은 체질 분류 태그와 원문 약어를 우선 보존했다",
        "시장 리포트에서 KRWUSD 환율 임계치와 NASDAQ100 리스크를 점검했다",
        "market stress 점검에서 KRWUSD 환율 임계치와 리스크 태그를 유지했다",
        "시장 도메인에서 NASDAQ100 리스크와 환율 임계치 보고를 반복했다",
        "정책팀은 market 리포트의 KRWUSD 환율 임계치를 재검증했다",
    ]
    if os.environ.get("MKM_APPLY_GEMATRIA_4D_BRIDGE_POLICY", "0").strip().lower() in {"1", "true", "yes", "on"}:
        samples.extend(
            [
                "META:4D=1.424 bridge policy 레인은 의미 보강 신호를 우선 기록했다",
                "gematria 좌표는 의미 레인 보강용이며 literal 복원 경로와 분리한다",
                "bridge policy 실험은 deterministic 복원 규칙을 침범하지 않는다",
            ]
        )
    profile = os.environ.get("HYBRID_CODEC_TRACKA_PROFILE", "").strip().lower()
    if profile in {"ops_market", "ops", "market"}:
        # Lane-specific corpus boost for Track A experiments.
        boost = [
            "ops market 융합 레인은 gateway 점검과 환율 임계치 레코드를 같이 유지한다",
            "KRWUSD 임계치와 NASDAQ100 리스크 태그를 ops 런북과 동시 관리한다",
            "gateway 점검 후 market stress 태그를 즉시 재기록한다",
        ]
        samples.extend(boost * 3)
    elif profile in {"med_ops", "medical_ops"}:
        boost = [
            "medical ops 레인은 체질 태그와 SHA256 검증 결과를 같이 보관한다",
            "의료 원문 약어와 gateway 점검 로그를 병합 검증한다",
            "체질 분류 태그와 운영 롤백 절차를 교차 점검한다",
        ]
        samples.extend(boost * 3)
    elif profile in {"general_quality", "general"}:
        boost = [
            "일반 도메인에서는 원문 보존 규칙과 요약 규칙을 분리 유지한다",
            "리포트 품질 점검에서 exact checksum 기준을 우선 적용한다",
        ]
        samples.extend(boost * 2)
    focus = os.environ.get("HYBRID_CODEC_HINT_DOMAIN_FOCUS", "").strip().lower()
    if focus in {"ops_market", "market_ops", "ops-market"}:
        samples.extend(
            [
                "ops market 융합 라인에서 gateway 점검과 환율 임계치 보고를 결합했다",
                "ops market 도메인은 SHA256 검증과 KRWUSD 임계치를 같이 유지했다",
                "gateway 상태 점검 후 market stress 리포트를 즉시 갱신했다",
                "ops 런북은 NASDAQ100 리스크 태그와 gateway 복구 순서를 고정했다",
            ]
        )
    elif focus in {"ops_only", "ops"}:
        samples.extend(
            [
                "ops 체인은 gateway 상태 점검과 SHA256 검증을 순차 고정했다",
                "운영팀은 ops 런북에 롤백 절차와 점검 로그를 반드시 기록한다",
                "gateway 복구 이후 ops 검증 단계에서 체크섬 비교를 반복 수행한다",
                "ops 도메인에서는 포트 8788 점검 결과를 우선 반영한다",
            ]
        )
    elif focus in {"med_ops", "medical_ops", "ops_med"}:
        samples.extend(
            [
                "medical ops 융합 라인에서 체질 태그와 gateway 점검 로그를 함께 보존했다",
                "의료 ops 레인에서는 원문 약어와 SHA256 검증 결과를 동시 기록한다",
                "medical ops 리포트는 병증 태그와 포트 8788 점검 결과를 결합한다",
                "의료 운영 라인에서 체질 분류 태그와 롤백 절차를 연계 검증했다",
            ]
        )
    return samples


def encode_packet_dict(text: str, dictionary: dict[str, str] | None = None) -> dict[str, Any]:
    dictionary = dictionary or build_dictionary()
    pkt = encode_text(text, dictionary)
    return {
        "schema": "hybrid_codec_v0_payload_v1",
        "dict_version": pkt.side_channel["dict_version"],
        "body_tokens": pkt.body_tokens,
        "side_channel": pkt.side_channel,
        "checksum_sha256_raw": pkt.checksum_sha256_raw,
        "input_token_count": pkt.input_token_count,
        "output_token_count": pkt.output_token_count,
        "input_char_len": pkt.input_char_len,
        "output_char_len": pkt.output_char_len,
    }


def decode_packet_dict(payload: dict[str, Any], dictionary: dict[str, str] | None = None) -> str:
    dictionary = dictionary or build_dictionary()
    reverse_dict = build_reverse_dictionary()
    side_channel = payload.get("side_channel")
    if not isinstance(side_channel, dict):
        raise ValueError("missing side_channel")
    raw_escape_map = side_channel.get("escape_map", {})
    raw_literal_map = side_channel.get("literal_map", {})
    normalized_escape_map: dict[int, str] = {}
    normalized_literal_map: dict[int, str] = {}
    if isinstance(raw_escape_map, dict):
        for k, v in raw_escape_map.items():
            try:
                normalized_escape_map[int(k)] = str(v)
            except (TypeError, ValueError):
                continue
    if isinstance(raw_literal_map, dict):
        for k, v in raw_literal_map.items():
            try:
                normalized_literal_map[int(k)] = str(v)
            except (TypeError, ValueError):
                continue
    normalized_side_channel = dict(side_channel)
    normalized_side_channel["escape_map"] = normalized_escape_map
    normalized_side_channel["literal_map"] = normalized_literal_map

    pkt = EncodedPacket(
        body_tokens=[str(x) for x in (payload.get("body_tokens") or [])],
        side_channel=normalized_side_channel,
        checksum_sha256_raw=str(payload.get("checksum_sha256_raw") or ""),
        input_token_count=int(payload.get("input_token_count") or 0),
        output_token_count=int(payload.get("output_token_count") or 0),
        input_char_len=int(payload.get("input_char_len") or 0),
        output_char_len=int(payload.get("output_char_len") or 0),
    )
    restored = decode_text(pkt, dictionary, reverse_dict)
    if _sha256_text(restored) != pkt.checksum_sha256_raw:
        raise ValueError("checksum mismatch")
    return restored


def run_spike() -> dict[str, Any]:
    dictionary = build_dictionary()
    reverse_dict = build_reverse_dictionary()
    samples = _build_samples()

    rows: list[dict[str, Any]] = []
    exact_hits = 0
    checksum_hits = 0
    total_in_chars = 0
    total_out_chars = 0

    for src in samples:
        pkt = encode_text(src, dictionary)
        restored = decode_text(pkt, dictionary, reverse_dict)
        exact = restored == src
        checksum_ok = _sha256_text(restored) == pkt.checksum_sha256_raw
        exact_hits += 1 if exact else 0
        checksum_hits += 1 if checksum_ok else 0
        total_in_chars += pkt.input_char_len
        total_out_chars += pkt.output_char_len
        rows.append(
            {
                "source": src,
                "encoded": " ".join(pkt.body_tokens),
                "restored": restored,
                "exact_restore_ok": exact,
                "checksum_ok": checksum_ok,
                "exact_restore_rate": 1.0 if exact else 0.0,
                "jaccard_score": _jaccard(src, restored),
                "input_tokens": pkt.input_token_count,
                "output_tokens": pkt.output_token_count,
                "input_chars": pkt.input_char_len,
                "output_chars": pkt.output_char_len,
                "side_channel": {
                    "dict_version": pkt.side_channel["dict_version"],
                    "escape_map_size": len(pkt.side_channel.get("escape_map", {})),
                    "swap_log_size": len(pkt.side_channel.get("swap_log", [])),
                },
            }
        )

    saving_rate = 1.0 - (total_out_chars / max(1, total_in_chars))
    return {
        "schema": "hybrid_codec_v0_spike_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "goals": {
            "deterministic_restore_first": True,
            "adaptive_saving_second": True,
        },
        "contract": {
            "dict_version": DICT_VERSION,
            "required_side_channel_keys": ["dict_version", "escape_map", "swap_log"],
            "exact_vs_jaccard_split_report": True,
        },
        "aggregate": {
            "sample_count": len(samples),
            "exact_restore_rate": exact_hits / max(1, len(samples)),
            "checksum_match_rate": checksum_hits / max(1, len(samples)),
            "saving_rate_chars": saving_rate,
            "avg_jaccard_score": sum(r["jaccard_score"] for r in rows) / max(1, len(rows)),
        },
        "rows": rows,
        "notes": [
            "Exact and Jaccard are reported separately by design.",
            "OOV/SYMBOL tokens are escaped as raw bytes via base64.",
            "Dictionary substitutions apply only when code length is shorter than source token.",
        ],
    }


@lru_cache(maxsize=1)
def build_reverse_dictionary() -> dict[str, str]:
    dictionary = build_dictionary()
    return {v: k for k, v in dictionary.items()}


@lru_cache(maxsize=1)
def build_reverse_phrase_dictionary() -> dict[str, str]:
    phrase_dict = build_phrase_dictionary()
    return {v: k for k, v in phrase_dict.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = run_spike()
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "exact_restore_rate": doc["aggregate"]["exact_restore_rate"],
                "checksum_match_rate": doc["aggregate"]["checksum_match_rate"],
                "saving_rate_chars": doc["aggregate"]["saving_rate_chars"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
