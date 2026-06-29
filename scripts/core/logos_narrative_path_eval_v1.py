"""B-track narrative path eval (HYPO) — separate from Track A alignment_pass_rate."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
ROUTER_SCRIPT = ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"


def _load_bridge(path: Path = BRIDGE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resonance_index(bridge: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for edge in bridge.get("resonance_edges") or []:
        src = str(edge.get("src_anchor_id") or "")
        dst = str(edge.get("dst_anchor_id") or "")
        if src and dst:
            pairs.add((src, dst))
            pairs.add((dst, src))
    return pairs


def _hop_pair_coherent(
    a: dict[str, Any],
    b: dict[str, Any],
    resonance: set[tuple[str, str]],
) -> bool:
    aid = str(a.get("anchor_id") or "")
    bid = str(b.get("anchor_id") or "")
    if (aid, bid) in resonance:
        return True
    if a.get("top_primitive") and a.get("top_primitive") == b.get("top_primitive"):
        return True
    ta = set(a.get("themed_bridge_ids") or [])
    tb = set(b.get("themed_bridge_ids") or [])
    if ta & tb:
        return True
    av = str(a.get("verse_ref") or "")
    bv = str(b.get("verse_ref") or "")
    ot_a = av.startswith(("Isa.", "Ps.", "Gen.", "Exod.", "Lev.", "Jer.", "Job."))
    nt_b = bv.startswith(("Jhn.", "Matt.", "Luke.", "Mark.", "Rom.", "Acts.", "Heb."))
    if ot_a and nt_b:
        return True
    return False


def eval_narrative_sample(
    sample: dict[str, Any],
    *,
    resonance: set[tuple[str, str]],
    run_router: bool = True,
) -> dict[str, Any]:
    path = list(sample.get("path") or [])
    edge_types = list(sample.get("edge_types") or [])
    hop_count = len(path)
    path_ok = hop_count >= 2 and all(
        hop.get("anchor_id") and hop.get("verse_ref") for hop in path
    )
    hypo_ok = sample.get("hypothesis_class") == "HYPO" and sample.get("non_gating") is True
    flow_pairs = max(hop_count - 1, 0)
    coherent_pairs = 0
    for i in range(flow_pairs):
        if _hop_pair_coherent(path[i], path[i + 1], resonance):
            coherent_pairs += 1
    if "curated_narrative_transition" in edge_types:
        flow_pass = True
        flow_score = 1.0
    else:
        flow_pass = flow_pairs == 0 or coherent_pairs == flow_pairs
        flow_score = (coherent_pairs / flow_pairs) if flow_pairs else 1.0

    router_hit = None
    router_paths = 0
    if run_router and ROUTER_SCRIPT.is_file():
        query = str(sample.get("query_ko") or "").strip()
        if query:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                out_path = Path(tmp.name)
            try:
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(ROUTER_SCRIPT),
                        "--query",
                        query,
                        "--output-json",
                        str(out_path),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0 and out_path.is_file():
                    router_doc = json.loads(out_path.read_text(encoding="utf-8"))
                    router_paths = len(router_doc.get("paths") or [])
                    verse_ids = set(router_doc.get("verse_ids") or [])
                    path_verses = {str(h.get("verse_ref")) for h in path if h.get("verse_ref")}
                    router_hit = bool(verse_ids & path_verses) or router_paths > 0
            finally:
                out_path.unlink(missing_ok=True)

    sample_pass = path_ok and hypo_ok and flow_pass
    return {
        "sample_id": sample.get("sample_id"),
        "path_ok": path_ok,
        "hypo_ok": hypo_ok,
        "flow_pass": flow_pass,
        "flow_score": round(flow_score, 4),
        "hop_count": hop_count,
        "router_hit": router_hit,
        "router_paths": router_paths,
        "sample_pass": sample_pass,
    }


def build_narrative_path_eval_report(
    bridge: dict[str, Any] | None = None,
    *,
    run_router: bool = True,
) -> dict[str, Any]:
    bridge = bridge or _load_bridge()
    samples = list(bridge.get("narrative_path_samples") or [])
    resonance = _resonance_index(bridge)
    rows = [eval_narrative_sample(s, resonance=resonance, run_router=run_router) for s in samples]
    n = len(rows)
    path_ok_count = sum(1 for r in rows if r["path_ok"])
    flow_pass_count = sum(1 for r in rows if r["flow_pass"])
    sample_pass_count = sum(1 for r in rows if r["sample_pass"])
    router_hit_count = sum(1 for r in rows if r.get("router_hit"))
    router_ran = sum(1 for r in rows if r.get("router_hit") is not None)

    return {
        "schema": "logos_narrative_path_eval_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "note_ko": (
            "B-track narrative routing eval — NOT Track A alignment_pass_rate. "
            "Curated path structure + flow coherence + optional router overlap."
        ),
        "narrative_sample_count": n,
        "summary": {
            "path_ok_rate": round(path_ok_count / n, 4) if n else 0.0,
            "flow_pass_rate": round(flow_pass_count / n, 4) if n else 0.0,
            "sample_pass_rate": round(sample_pass_count / n, 4) if n else 0.0,
            "router_hit_rate": round(router_hit_count / router_ran, 4) if router_ran else None,
            "path_ok_count": path_ok_count,
            "flow_pass_count": flow_pass_count,
            "sample_pass_count": sample_pass_count,
            "router_hit_count": router_hit_count,
        },
        "samples": rows,
        "reproducible_command": "py scripts/run_logos_narrative_path_eval_chain_v1.py",
    }
