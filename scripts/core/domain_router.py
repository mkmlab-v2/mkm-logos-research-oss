# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.6, M:0.4}
# Balance: 90
# Purpose: Route text to domain-specific codebook shards.
# Keywords: router, domain, codebook, shard, compression
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# When no routing_keywords hit any shard (max score 0), route Hangul-heavy text here
# instead of zone_d_ssot so general-Korean prose gets hangul_principle + zone_c caps.
HANGUL_RATIO_FALLBACK_ZONE_C = 0.35


@dataclass(frozen=True)
class ShardRoute:
    shard_id: str
    domain: str
    must_keep_hard_terms: tuple[str, ...]
    must_keep_soft_terms: tuple[str, ...]
    guard_tokens: tuple[str, ...]
    hangul_principle: bool


class DomainSpecificRouter:
    """Minimal domain router for compression shard selection."""

    def __init__(self, shards_root: Path) -> None:
        self._root = shards_root
        self._shards = self._load_shards()

    @staticmethod
    def _hangul_ratio(text: str) -> float:
        if not text:
            return 0.0
        n = sum(1 for ch in text if "\uac00" <= ch <= "\ud7a3")
        return n / len(text)

    def _shard_by_id(self, shard_id: str) -> dict | None:
        sid = str(shard_id).lower()
        for s in self._shards:
            if str(s.get("shard_id", "")).lower() == sid:
                return s
        return None

    def _shard_dict_to_route(self, best: dict) -> ShardRoute:
        return ShardRoute(
            shard_id=str(best.get("shard_id", "zone_d_ssot")),
            domain=str(best.get("domain", "ssot")),
            must_keep_hard_terms=tuple(
                str(x).lower() for x in best.get("must_keep_hard_terms", best.get("must_keep_terms", []))
            ),
            must_keep_soft_terms=tuple(str(x).lower() for x in best.get("must_keep_soft_terms", [])),
            guard_tokens=tuple(str(x).lower() for x in best.get("guard_tokens", [])),
            hangul_principle=bool(best.get("hangul_principle", False)),
        )

    def route_from_shard_id(self, shard_id: str) -> ShardRoute:
        """Build a ShardRoute from a shard JSON by id (ablation / forced-Psi without keyword scoring)."""
        d = self._shard_by_id(shard_id)
        if d is None:
            known = sorted({str(s.get("shard_id", "")) for s in self._shards if s.get("shard_id")})
            raise ValueError(f"Unknown shard_id {shard_id!r}; known: {known}")
        return self._shard_dict_to_route(d)

    def route(self, text: str) -> ShardRoute:
        words = {w.lower() for w in re.findall(r"[A-Za-z0-9_가-힣]+", text)}
        scored: list[tuple[int, dict]] = []
        for shard in self._shards:
            keys = {str(k).lower() for k in shard.get("routing_keywords", [])}
            score = sum(1 for k in keys if k in words)
            scored.append((score, shard))
        if not scored:
            best = self._default_shard()
        else:
            best_score, best = max(scored, key=lambda x: x[0])
            if best_score <= 0:
                zc = self._shard_by_id("zone_c_hangul")
                if zc is not None and self._hangul_ratio(text) >= HANGUL_RATIO_FALLBACK_ZONE_C:
                    best = zc
                else:
                    best = self._preferred_default_shard()
        return self._shard_dict_to_route(best)

    def _load_shards(self) -> list[dict]:
        if not self._root.is_dir():
            return [self._default_shard()]
        files = sorted(self._root.glob("zone_*.json"))
        out: list[dict] = []
        for f in files:
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue
        return out or [self._default_shard()]

    def _preferred_default_shard(self) -> dict:
        for s in self._shards:
            if str(s.get("shard_id", "")).lower() == "zone_d_ssot":
                return s
        return self._default_shard()

    @staticmethod
    def _default_shard() -> dict:
        return {
            "shard_id": "zone_d_ssot",
            "domain": "ssot",
            "routing_keywords": [],
            "must_keep_hard_terms": [],
            "must_keep_soft_terms": [],
            "guard_tokens": [],
            "hangul_principle": False,
        }
