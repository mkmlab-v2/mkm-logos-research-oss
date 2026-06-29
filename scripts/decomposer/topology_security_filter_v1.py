#!/usr/bin/env python3
"""GRASP-inspired topology export sanitizer — ID alignment + decoy injection [HYPO].

Scope: public stub export only (`tests/fixtures/logos_verse_4d_topology_stub_v1.jsonl`).
Defense reference: arXiv:2602.06495 (ID alignment + decoy).
send_gate: HOLD — research_only, not Track A promotion.
"""
from __future__ import annotations

import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_DECOY_RATIO = 0.15
DEFAULT_Q_THRESHOLD = 0.25
DEFAULT_RELATION = "has_atom"
DECOY_RELATION = "corresponds_with"


@dataclass
class TopologicalDecomposerSanitizer:
    """GraphRAG export sanitizer: ephemeral virtual IDs + decoy topology."""

    decoy_ratio: float = DEFAULT_DECOY_RATIO
    q_threshold: float = DEFAULT_Q_THRESHOLD
    virtual_id_registry: dict[str, str] = field(default_factory=dict)
    q_table: dict[str, float] = field(default_factory=dict)
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def reset_session(self) -> None:
        self.virtual_id_registry.clear()
        self.session_id = uuid.uuid4().hex[:12]

    def dynamic_id_alignment(self, graph_triplets: list[dict[str, str]]) -> list[dict[str, Any]]:
        aligned: list[dict[str, Any]] = []
        for triplet in graph_triplets:
            src = str(triplet["src"])
            rel = str(triplet["relation"])
            dst = str(triplet["dst"])
            if src not in self.virtual_id_registry:
                self.virtual_id_registry[src] = f"v_node_{uuid.uuid4().hex[:8]}"
            if dst not in self.virtual_id_registry:
                self.virtual_id_registry[dst] = f"v_node_{uuid.uuid4().hex[:8]}"
            aligned.append(
                {
                    "src": self.virtual_id_registry[src],
                    "relation": rel,
                    "dst": self.virtual_id_registry[dst],
                    "instance_id": f"inst_{uuid.uuid4().hex[:6]}",
                    "is_decoy": False,
                    "session_id": self.session_id,
                }
            )
        return aligned

    def inject_decoy_topology(self, aligned_triplets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        real_count = sum(1 for t in aligned_triplets if not t.get("is_decoy"))
        total_decoys = int(real_count * self.decoy_ratio)
        out = list(aligned_triplets)
        for _ in range(total_decoys):
            out.append(
                {
                    "src": f"v_node_decoy_{uuid.uuid4().hex[:8]}",
                    "relation": DECOY_RELATION,
                    "dst": f"v_node_decoy_{uuid.uuid4().hex[:8]}",
                    "instance_id": f"inst_decoy_{uuid.uuid4().hex[:6]}",
                    "is_decoy": True,
                    "session_id": self.session_id,
                }
            )
        return out

    def evaluate_q_gate(self, stage_id: str, feedback_reward: float) -> bool:
        current_q = self.q_table.get(stage_id, 0.5)
        updated_q = current_q + 0.1 * (feedback_reward - current_q)
        self.q_table[stage_id] = updated_q
        return updated_q >= self.q_threshold

    def sanitize(self, graph_triplets: list[dict[str, str]]) -> list[dict[str, Any]]:
        aligned = self.dynamic_id_alignment(graph_triplets)
        return self.inject_decoy_topology(aligned)


def jsonl_stub_to_triplets(
    jsonl_path: Path,
    *,
    max_rows: int | None = None,
    relation: str = DEFAULT_RELATION,
) -> list[dict[str, str]]:
    """Verse→atom edges from public topology stub JSONL."""
    triplets: list[dict[str, str]] = []
    if not jsonl_path.is_file():
        return triplets
    with jsonl_path.open(encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            if max_rows is not None and idx >= max_rows:
                break
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            verse_id = str(row.get("verse_id") or "").strip()
            if not verse_id:
                continue
            atoms = ((row.get("atom_overlay") or {}).get("top_atoms")) or []
            for atom in atoms:
                atom_id = str(atom.get("atom_id") or "").strip()
                if not atom_id:
                    continue
                triplets.append({"src": verse_id, "relation": relation, "dst": atom_id})
    return triplets


def sanitize_topology_triplets(
    graph_triplets: list[dict[str, str]],
    *,
    decoy_ratio: float = DEFAULT_DECOY_RATIO,
    reset_session: bool = True,
) -> dict[str, Any]:
    sanitizer = TopologicalDecomposerSanitizer(decoy_ratio=decoy_ratio)
    if reset_session:
        sanitizer.reset_session()
    sanitized = sanitizer.sanitize(graph_triplets)
    real = [t for t in sanitized if not t.get("is_decoy")]
    decoys = [t for t in sanitized if t.get("is_decoy")]
    return {
        "schema": "topology_security_sanitize_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "session_id": sanitizer.session_id,
        "real_triplet_count": len(real),
        "decoy_triplet_count": len(decoys),
        "decoy_ratio_applied": (len(decoys) / len(real)) if real else 0.0,
        "sanitized_triplets": sanitized,
        "virtual_id_count": len(sanitizer.virtual_id_registry),
    }


def _node_degrees(triplets: list[dict[str, Any]], *, include_decoys: bool) -> dict[str, int]:
    deg: dict[str, int] = defaultdict(int)
    for triplet in triplets:
        if triplet.get("is_decoy") and not include_decoys:
            continue
        deg[str(triplet["src"])] += 1
        deg[str(triplet["dst"])] += 1
    return dict(deg)


def estimate_grasp_reconstruction_f1(
    truth_triplets: list[dict[str, str]],
    sanitized_triplets: list[dict[str, Any]],
) -> dict[str, float]:
    """Naive structural attacker: degree-order node matching (GRASP-style profiling upper bound)."""
    truth_edges = {(t["src"], t["relation"], t["dst"]) for t in truth_triplets}
    truth_nodes = {n for e in truth_edges for n in (e[0], e[2])}

    leak_nodes = {str(t["src"]) for t in sanitized_triplets} | {str(t["dst"]) for t in sanitized_triplets}
    truth_deg = _node_degrees(
        [{"src": a, "dst": c, "relation": b, "is_decoy": False} for a, b, c in truth_edges],
        include_decoys=True,
    )
    leak_deg = _node_degrees(sanitized_triplets, include_decoys=True)

    sorted_truth = sorted(truth_nodes, key=lambda n: (-truth_deg.get(n, 0), n))
    sorted_leak = sorted(leak_nodes, key=lambda n: (-leak_deg.get(n, 0), n))
    mapping = {lv: tv for lv, tv in zip(sorted_leak, sorted_truth)}

    predicted_edges: set[tuple[str, str, str]] = set()
    for triplet in sanitized_triplets:
        src = mapping.get(str(triplet["src"]))
        dst = mapping.get(str(triplet["dst"]))
        if src and dst:
            predicted_edges.add((src, str(triplet["relation"]), dst))

    tp = len(predicted_edges & truth_edges)
    fp = len(predicted_edges - truth_edges)
    fn = len(truth_edges - predicted_edges)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": float(tp),
        "false_positives": float(fp),
        "false_negatives": float(fn),
    }


def assert_no_canonical_id_leak(sanitized: list[dict[str, Any]], canonical_ids: set[str]) -> list[str]:
    leaks: list[str] = []
    for cid in canonical_ids:
        needle = cid.lower()
        if not needle:
            continue
        for triplet in sanitized:
            for key in ("src", "dst", "instance_id"):
                val = str(triplet.get(key) or "")
                if needle in val.lower():
                    leaks.append(f"{key}:{val} contains {cid}")
    return leaks


def main() -> int:
    import argparse
    import sys
    from datetime import datetime, timezone

    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--stub",
        type=Path,
        default=root / "tests/fixtures/logos_verse_4d_topology_stub_v1.jsonl",
    )
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--decoy-ratio", type=float, default=DEFAULT_DECOY_RATIO)
    ap.add_argument("--f1-gate", type=float, default=0.15)
    ap.add_argument(
        "--out",
        type=Path,
        default=root / "reports/topology_grasp_defense_bench_v1_latest.json",
    )
    args = ap.parse_args()

    truth = jsonl_stub_to_triplets(args.stub, max_rows=args.max_rows)
    if not truth:
        print(f"no triplets from {args.stub}", file=sys.stderr)
        return 1

    package = sanitize_topology_triplets(truth, decoy_ratio=args.decoy_ratio)
    sanitized = package["sanitized_triplets"]
    canonical = {t["src"] for t in truth} | {t["dst"] for t in truth}
    leaks = assert_no_canonical_id_leak(sanitized, canonical)
    metrics = estimate_grasp_reconstruction_f1(truth, sanitized)
    gate_ok = metrics["f1"] <= args.f1_gate and not leaks

    payload = {
        **package,
        "grasp_defense_metrics": metrics,
        "canonical_id_leaks": leaks,
        "f1_gate": args.f1_gate,
        "gate_ok": gate_ok,
        "stub_path": str(args.stub.relative_to(root)) if args.stub.is_relative_to(root) else str(args.stub),
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    del payload["sanitized_triplets"]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"gate_ok": gate_ok, "f1": metrics["f1"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
