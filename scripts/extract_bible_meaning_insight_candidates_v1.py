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
    ap=argparse.ArgumentParser(); ap.add_argument('--nodes-jsonl', required=True); ap.add_argument('--edges-jsonl', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    np,ep,op=Path(a.nodes_jsonl),Path(a.edges_jsonl),Path(a.output_json)
    if not np.is_absolute(): np=ROOT/np
    if not ep.is_absolute(): ep=ROOT/ep
    if not op.is_absolute(): op=ROOT/op
    nodes=loadj(np); edges=loadj(ep)
    top=[]
    for i,n in enumerate(nodes[:20]):
        nid=str(n.get('node_id',''))
        deg=sum(1 for e in edges if str(e.get('src_node_id',''))==nid or str(e.get('dst_node_id',''))==nid)
        top.append({'candidate_id':f'cand_{i+1:03d}','source_node_id':nid,'hub_score':min(1.0,deg/10.0),'path_score':0.55,'cluster_size':max(1,deg),'regime_tag':(n.get('regime_tags') or ['unknown'])[0]})
    doc={'schema':'bible_meaning_insight_candidates_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','candidates':top}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
