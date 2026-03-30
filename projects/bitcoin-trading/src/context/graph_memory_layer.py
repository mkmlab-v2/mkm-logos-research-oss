#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Graph Memory Layer for MKM12 Phase 1.

Converts unstructured text into timestamped triples and appends them as JSONL.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class Triple:
    subject: str
    relation: str
    obj: str
    confidence: float


class GraphMemoryLayer:
    """Minimal graph-memory extractor and JSONL writer."""

    _EDGE_RULES = [
        (r"(수익률|손실|drawdown|손해|청산)", "Wealth", "impacts", "Health", 0.75),
        (r"(잠|불면|수면|피곤|피로)", "Health", "correlates_with", "Habit", 0.7),
        (r"(스트레스|불안|압박|번아웃)", "Project", "causes", "Health", 0.78),
        (r"(매매봇|트레이딩|비트코인|BTC|알고리즘)", "Project", "depends_on", "Signal", 0.72),
        (r"(관계|가족|동료|갈등|대화)", "Relationship", "affects", "Health", 0.68),
    ]

    def __init__(self, output_jsonl: Path):
        self.output_jsonl = output_jsonl
        self.output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    def extract_triples(self, text: str) -> List[Triple]:
        triples: List[Triple] = []
        normalized = text.strip()
        if not normalized:
            return triples

        for pattern, subject, relation, obj, confidence in self._EDGE_RULES:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                triples.append(
                    Triple(
                        subject=subject,
                        relation=relation,
                        obj=obj,
                        confidence=confidence,
                    )
                )

        return self._dedupe(triples)

    def append_events(
        self,
        message_id: str,
        text: str,
        observed_at: datetime | None = None,
        source: str = "chat",
    ) -> int:
        triples = self.extract_triples(text)
        if not triples:
            return 0

        ts = observed_at or datetime.now(timezone.utc)
        lines = [
            json.dumps(
                {
                    "event_id": self._event_id(message_id, t, ts),
                    "source_message_id": message_id,
                    "source": source,
                    "observed_at": ts.isoformat(),
                    "subject": t.subject,
                    "relation": t.relation,
                    "object": t.obj,
                    "confidence": t.confidence,
                    "text": text,
                },
                ensure_ascii=False,
            )
            for t in triples
        ]

        with self.output_jsonl.open("a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

        return len(lines)

    @staticmethod
    def _event_id(message_id: str, triple: Triple, ts: datetime) -> str:
        payload = f"{message_id}|{triple.subject}|{triple.relation}|{triple.obj}|{ts.isoformat()}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _dedupe(triples: Iterable[Triple]) -> List[Triple]:
        seen = set()
        result = []
        for t in triples:
            key = (t.subject, t.relation, t.obj)
            if key in seen:
                continue
            seen.add(key)
            result.append(t)
        return result
