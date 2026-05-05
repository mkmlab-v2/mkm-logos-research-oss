#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def loadj(path):
    out=[]
    for l in path.read_text(encoding='utf-8-sig').splitlines():
        s=l.strip()
        if not s: continue
        try:o=json.loads(s)
        except Exception: continue
        if isinstance(o,dict): out.append(o)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--edges-jsonl', required=True); ap.add_argument('--bridge-edges-jsonl'); ap.add_argument('--include-bridge-edges', action='store_true'); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    ep=Path(a.edges_jsonl); bp=Path(a.bridge_edges_jsonl) if a.bridge_edges_jsonl else None; op=Path(a.output_json)
    if not ep.is_absolute(): ep=ROOT/ep
    if bp and not bp.is_absolute(): bp=ROOT/bp
    if not op.is_absolute(): op=ROOT/op
    edges=loadj(ep)
    if a.include_bridge_edges and bp and bp.is_file(): edges.extend(loadj(bp))
    n=max(1,len(edges)); ov=sum(float(e.get('semantic_overlap',0.0)) for e in edges)/n; sh=sum(int(e.get('shared_token_count',0)) for e in edges)/n
    hist={}
    for e in edges:
        t=str(e.get('edge_type','unknown')); hist[t]=hist.get(t,0)+1
    doc={'schema':'aramaic_semantic_edge_quality_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','edge_count':len(edges),'semantic_overlap_mean':round(ov,6),'shared_token_mean':round(sh,6),'edge_type_histogram':hist}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
