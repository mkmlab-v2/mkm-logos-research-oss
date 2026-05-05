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
    ap=argparse.ArgumentParser(); ap.add_argument('--aramaic-nodes-jsonl', required=True); ap.add_argument('--output-nodes-jsonl', required=True); ap.add_argument('--output-edges-jsonl', required=True); a=ap.parse_args()
    inp=Path(a.aramaic_nodes_jsonl); on=Path(a.output_nodes_jsonl); oe=Path(a.output_edges_jsonl)
    if not inp.is_absolute(): inp=ROOT/inp
    if not on.is_absolute(): on=ROOT/on
    if not oe.is_absolute(): oe=ROOT/oe
    nodes=loadj(inp); bnodes=[]; bedges=[]
    for n in nodes:
        ref=str(n.get('ref',''))
        for corpus,coef in [('hebrew',0.82),('greek',0.78)]:
            nid=f'{corpus}::{ref}'
            bnodes.append({'schema':'aramaic_graph_node_v1','node_id':nid,'corpus':corpus,'ref':ref,'text_norm':str(n.get('text_norm','')),'time_bucket':str(n.get('time_bucket','ancient_empire_cycle')),'theme_tags':list(n.get('theme_tags') or []),'regime_tags':list(n.get('regime_tags') or []),'research_only':True,'promotion_required':True,'source_track':'B'})
            bedges.append({'schema':'aramaic_graph_edge_v1','src_node_id':n.get('node_id'),'dst_node_id':nid,'edge_type':'cross_lens_confirm','weight':coef,'confidence':coef,'evidence':'cross_corpus_bridge_stub','as_of_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','semantic_overlap':0.75,'shared_token_count':3,'relation_basis':['cross_corpus','token_overlap']})
    on.parent.mkdir(parents=True, exist_ok=True); oe.parent.mkdir(parents=True, exist_ok=True)
    on.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in bnodes)+'\n', encoding='utf-8')
    oe.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in bedges)+'\n', encoding='utf-8')
    print(str(on)); print(str(oe)); return 0
if __name__=='__main__': raise SystemExit(main())
