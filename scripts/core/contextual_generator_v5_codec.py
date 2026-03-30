from __future__ import annotations

import json
import re
from pathlib import Path


def _split_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_가-힣]+|[א-ת]+|[Α-Ωα-ωϛϟϡ]+", text)


class ContextualGeneratorV5Codec:
    """Slot-id codec prototype: compact ids + template reconstruction."""

    def __init__(self, slot_dict_path: Path | None = None) -> None:
        self._slot_terms: dict[str, set[str]] = {
            "S1": {"state", "명리", "state_id"},
            "S2": {"policy", "boundary", "trigger"},
            "S3": {"evidence", "direct", "witness", "traceability", "증거", "직접"},
            "S4": {"manual", "strict", "review", "gate", "수동", "엄격"},
            "S5": {"체질", "사상의학", "sasang"},
            "S6": {"성경", "bible", "logos"},
            "S7": {"alignment", "cadence", "timeline"},
        }
        self._slot_templates: dict[str, str] = {
            "S1": "state-transition context",
            "S2": "policy boundary and trigger",
            "S3": "direct witness evidence traceability",
            "S4": "manual strict review gate",
            "S5": "sasang constitution constraint",
            "S6": "bible logos alignment",
            "S7": "cadence timeline alignment",
        }
        self._last_spans: dict[str, tuple[int, int]] = {}
        self._last_matched_slots: list[str] = []
        if slot_dict_path is not None and slot_dict_path.is_file():
            self._load_slot_dictionary(slot_dict_path)

    def _load_slot_dictionary(self, path: Path) -> None:
        doc = json.loads(path.read_text(encoding="utf-8"))
        slots = doc.get("slots") or {}
        for sid in ("S1", "S2", "S3", "S4", "S5", "S6", "S7"):
            values = slots.get(sid)
            if isinstance(values, list) and values:
                self._slot_terms[sid] = {str(v).lower() for v in values}

    def _extract_spans(self, raw: str) -> None:
        """Track first/last token index for each slot term hit."""
        words = [w.lower() for w in _split_words(raw)]
        self._last_spans = {}
        for sid, terms in self._slot_terms.items():
            indices = [i for i, w in enumerate(words) if w in terms]
            if not indices:
                continue
            self._last_spans[sid] = (min(indices), max(indices))

    def encode(self, *, raw: str, state16: int | None, must_keep: set[str]) -> str:
        words = [w.lower() for w in _split_words(raw)]
        self._extract_spans(raw)
        matched: list[str] = []
        must = {w.lower() for w in must_keep}
        self._last_matched_slots = []
        for sid, terms in self._slot_terms.items():
            if any((t in words) or (t in must) for t in terms):
                matched.append(sid)
                self._last_matched_slots.append(sid)
        if state16 is not None:
            matched.append(f"ST{int(state16):02d}")
        # Ensure deterministic and compact output.
        uniq: list[str] = []
        seen: set[str] = set()
        for tok in matched:
            if tok in seen:
                continue
            seen.add(tok)
            uniq.append(tok)
        return " ".join(uniq[:8])

    def decode(self, *, encoded: str, raw: str) -> str:
        toks = encoded.split()
        raw_tokens = _split_words(raw)
        if not raw_tokens:
            return encoded
        selected_idx: set[int] = set()
        for t in toks:
            if t.startswith("ST"):
                continue
            span = self._last_spans.get(t)
            if span is None:
                continue
            start, end = span
            # Include a small neighborhood around slot span for coherence.
            s = max(0, start - 1)
            e = min(len(raw_tokens) - 1, end + 1)
            for i in range(s, e + 1):
                selected_idx.add(i)
        if not selected_idx:
            # Fallback to template mode when no spans are available.
            out: list[str] = []
            for t in toks:
                if t.startswith("ST"):
                    out.append(f"state profile {t}")
                    continue
                template = self._slot_templates.get(t)
                if template:
                    out.append(template)
            return "; ".join(out) if out else encoded
        ordered = [raw_tokens[i] for i in sorted(selected_idx)]
        return " ".join(ordered)

    def decode_hybrid(self, *, encoded: str, raw: str, max_tokens_ratio: float = 0.52) -> str:
        """Hybrid decode: span reconstruction + token top-up within budget."""
        base = self.decode(encoded=encoded, raw=raw)
        raw_tokens = _split_words(raw)
        if not raw_tokens:
            return base
        budget = max(1, int(len(raw_tokens) * max_tokens_ratio))
        out_tokens = _split_words(base)
        out_l = {t.lower() for t in out_tokens}
        if len(out_tokens) >= budget:
            return " ".join(out_tokens[:budget])

        # Prioritize terms from matched slots that are present in raw.
        priority_terms: list[str] = []
        for sid in self._last_matched_slots:
            for t in self._slot_terms.get(sid, set()):
                priority_terms.append(t)
        for t in priority_terms:
            if len(out_tokens) >= budget:
                break
            if t in out_l:
                continue
            if t in {w.lower() for w in raw_tokens}:
                out_tokens.append(t)
                out_l.add(t)

        # Fill with earliest raw tokens not yet included.
        for t in raw_tokens:
            if len(out_tokens) >= budget:
                break
            tl = t.lower()
            if tl in out_l:
                continue
            out_tokens.append(t)
            out_l.add(tl)
        return " ".join(out_tokens)
