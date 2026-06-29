#!/usr/bin/env python3
"""Lightweight dependency-path + 2-simplex engine (DEMOCRITUS-inspired, Track B [HYPO])."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROLE_TYPES = frozenset({"Antecedent", "Intermediary", "Constraints", "Consequent", "Hub", "LogicRole"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LogosSimplicialEngine:
    """In-memory SQLite — dependency paths only (not causal identification)."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS logic_nodes (
                node_id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                logical_role TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dependency_edges (
                edge_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                polarity INTEGER DEFAULT 1,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY(source_id) REFERENCES logic_nodes(node_id),
                FOREIGN KEY(target_id) REFERENCES logic_nodes(node_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS simplicial_2 (
                complex_id TEXT PRIMARY KEY,
                node_u TEXT NOT NULL,
                node_v TEXT NOT NULL,
                node_w TEXT NOT NULL,
                coherence_weight REAL DEFAULT 1.0,
                FOREIGN KEY(node_u) REFERENCES logic_nodes(node_id),
                FOREIGN KEY(node_v) REFERENCES logic_nodes(node_id),
                FOREIGN KEY(node_w) REFERENCES logic_nodes(node_id)
            )
            """
        )
        self.conn.commit()

    def register_node(self, node_id: str, label: str, role: str) -> None:
        if role not in ROLE_TYPES:
            role = "LogicRole"
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO logic_nodes VALUES (?,?,?)",
            (node_id, label, role),
        )
        self.conn.commit()

    def register_edge(
        self, edge_id: str, src: str, tgt: str, *, polarity: int = 1, weight: float = 1.0
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO dependency_edges VALUES (?,?,?,?,?)",
            (edge_id, src, tgt, polarity, weight),
        )
        self.conn.commit()

    def register_triangle(self, complex_id: str, u: str, v: str, w: str, *, weight: float = 1.0) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO simplicial_2 VALUES (?,?,?,?,?)",
            (complex_id, u, v, w, weight),
        )
        self.conn.commit()

    def evaluate_path(self, start_id: str, end_id: str, *, max_hops: int = 3) -> dict[str, Any]:
        if start_id == end_id:
            return {
                "path_found": True,
                "path_type": "identity",
                "hop_count": 0,
                "requires_hitl": False,
            }

        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT target_id, polarity, weight FROM dependency_edges WHERE source_id = ?
            """,
            (start_id,),
        )
        for tgt, pol, w in cur.fetchall():
            if tgt == end_id:
                return {
                    "path_found": True,
                    "path_type": "direct_1_simplex",
                    "hop_count": 1,
                    "polarity": pol,
                    "weight": w,
                    "requires_hitl": w < 0.85,
                }

        if max_hops >= 2:
            cur.execute(
                """
                SELECT s.node_v, s.coherence_weight, e1.polarity, e2.polarity, e1.weight, e2.weight
                FROM simplicial_2 s
                JOIN dependency_edges e1 ON s.node_u = e1.source_id AND s.node_v = e1.target_id
                JOIN dependency_edges e2 ON s.node_v = e2.source_id AND s.node_w = e2.target_id
                WHERE s.node_u = ? AND s.node_w = ?
                """,
                (start_id, end_id),
            )
            row = cur.fetchone()
            if row:
                mid, cw, p1, p2, w1, w2 = row
                return {
                    "path_found": True,
                    "path_type": "simplicial_2_simplex",
                    "hop_count": 2,
                    "intermediary_node": mid,
                    "synthetic_polarity": int(p1) * int(p2),
                    "coherence_weight": cw,
                    "edge_weights": [w1, w2],
                    "requires_hitl": cw < 0.8,
                }

        cur.execute(
            """
            SELECT e2.target_id, e1.weight * e2.weight
            FROM dependency_edges e1
            JOIN dependency_edges e2 ON e1.target_id = e2.source_id
            WHERE e1.source_id = ? AND e2.target_id = ?
            """,
            (start_id, end_id),
        )
        row = cur.fetchone()
        if row:
            mid, combined = row
            return {
                "path_found": True,
                "path_type": "two_hop_dependency",
                "hop_count": 2,
                "intermediary_node": mid,
                "combined_weight": combined,
                "requires_hitl": combined < 0.75,
            }

        return {"path_found": False, "path_type": "none", "requires_hitl": True}

    def snapshot(self) -> dict[str, Any]:
        cur = self.conn.cursor()
        nodes = cur.execute("SELECT node_id, label, logical_role FROM logic_nodes").fetchall()
        edges = cur.execute(
            "SELECT edge_id, source_id, target_id, polarity, weight FROM dependency_edges"
        ).fetchall()
        triangles = cur.execute(
            "SELECT complex_id, node_u, node_v, node_w, coherence_weight FROM simplicial_2"
        ).fetchall()
        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "triangle_count": len(triangles),
            "nodes": [{"id": n[0], "label": n[1], "role": n[2]} for n in nodes],
            "edges": [
                {"id": e[0], "source": e[1], "target": e[2], "polarity": e[3], "weight": e[4]}
                for e in edges
            ],
            "triangles": [
                {"id": t[0], "u": t[1], "v": t[2], "w": t[3], "weight": t[4]} for t in triangles
            ],
        }


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema": "logos_track_b_research_v1",
            "version": "1.0.0",
            "lane": "track_b_hypo",
            "non_gating": True,
            "research_only": True,
            "content_layer_isolated": True,
            "records": [],
        }
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        doc = {}
    doc.setdefault("schema", "logos_track_b_research_v1")
    doc.setdefault("records", [])
    return doc


def append_ledger_record(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    doc = load_ledger(path)
    record = dict(record)
    record.setdefault("record_id", f"rec_{uuid.uuid4().hex[:12]}")
    record.setdefault("recorded_at_utc", _utc())
    records: list[dict[str, Any]] = list(doc.get("records") or [])
    dedupe_key = (
        record.get("record_type"),
        record.get("source_node"),
        record.get("target_node"),
    )
    records = [
        r
        for r in records
        if (r.get("record_type"), r.get("source_node"), r.get("target_node")) != dedupe_key
    ]
    records.append(record)
    doc["records"] = records[-500:]
    doc["generated_at_utc"] = _utc()
    doc["record_count"] = len(doc["records"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def replace_ledger_records_by_type(path: Path, record_type: str, new_records: list[dict[str, Any]]) -> dict[str, Any]:
    doc = load_ledger(path)
    kept = [r for r in (doc.get("records") or []) if r.get("record_type") != record_type]
    stamped: list[dict[str, Any]] = []
    for rec in new_records:
        row = dict(rec)
        row.setdefault("record_id", f"rec_{uuid.uuid4().hex[:12]}")
        row.setdefault("recorded_at_utc", _utc())
        row.setdefault("record_type", record_type)
        stamped.append(row)
    doc["records"] = (kept + stamped)[-500:]
    doc["generated_at_utc"] = _utc()
    doc["record_count"] = len(doc["records"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc
