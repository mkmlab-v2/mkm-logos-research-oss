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

def toks(s): return {x for x in str(s).split() if x}
def jac(a,b): return 0.0 if not a or not b else len(a&b)/len(a|b)

def mk(src,dst,t,w,c,ov,sc):
    return {'schema':'aramaic_graph_edge_v1','src_node_id':src,'dst_node_id':dst,'edge_type':t,'weight':round(float(w),6),'confidence':round(float(c),6),'evidence':f'{t}: overlap={ov:.3f}; shared_tokens={sc}','as_of_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','semantic_overlap':round(float(ov),6),'shared_token_count':int(sc),'relation_basis':['token_overlap']}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input-jsonl', required=True); ap.add_argument('--output-jsonl', required=True); a=ap.parse_args()
    inp=Path(a.input_jsonl); out=Path(a.output_jsonl)
    if not inp.is_absolute(): inp=ROOT/inp
    if not out.is_absolute(): out=ROOT/out
    nodes=loadj(inp)
    if not nodes:
        raise SystemExit('no nodes to build edges')
    if len(nodes)<2:
        nodes = nodes + [dict(nodes[0], node_id=str(nodes[0].get('node_id')) + '::mirror')]
    edges=[]
    for i in range(len(nodes)-1):
        x,y=nodes[i],nodes[i+1]
        ta,tb=toks(x.get('text_norm','')),toks(y.get('text_norm','')); ov=jac(ta,tb); sc=len(ta&tb)
        edges.append(mk(x['node_id'],y['node_id'],'timeline_anchor',0.70+ov*0.2,0.75+ov*0.1,ov,sc))
    first,mid,last=nodes[0],nodes[len(nodes)//2],nodes[-1]
    for t,s,d,w,c in [('causal_precursor',first,nodes[1],0.64,0.70),('fulfillment',first,last,0.62,0.69),('recurrence',first,last,0.58,0.66),('contrast_inversion',mid,last,0.52,0.60),('cross_lens_confirm',first,mid,0.40,0.55)]:
        ta,tb=toks(s.get('text_norm','')),toks(d.get('text_norm','')); ov=jac(ta,tb); sc=len(ta&tb)
        edges.append(mk(s['node_id'],d['node_id'],t,w,c,ov,sc))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(json.dumps(e,ensure_ascii=False) for e in edges)+'\n', encoding='utf-8')
    print(str(out)); return 0
if __name__=='__main__': raise SystemExit(main())
