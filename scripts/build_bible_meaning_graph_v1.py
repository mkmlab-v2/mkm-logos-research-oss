#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
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
    ap=argparse.ArgumentParser(); ap.add_argument('--verse-nodes-jsonl', required=True); ap.add_argument('--bridge-nodes-jsonl', required=True); ap.add_argument('--verse-edges-jsonl', required=True); ap.add_argument('--bridge-edges-jsonl', required=True); ap.add_argument('--output-nodes-jsonl', required=True); ap.add_argument('--output-edges-jsonl', required=True); a=ap.parse_args()
    vn,bn,ve,be,on,oe=[Path(x) for x in [a.verse_nodes_jsonl,a.bridge_nodes_jsonl,a.verse_edges_jsonl,a.bridge_edges_jsonl,a.output_nodes_jsonl,a.output_edges_jsonl]]
    if not vn.is_absolute(): vn=ROOT/vn
    if not bn.is_absolute(): bn=ROOT/bn
    if not ve.is_absolute(): ve=ROOT/ve
    if not be.is_absolute(): be=ROOT/be
    if not on.is_absolute(): on=ROOT/on
    if not oe.is_absolute(): oe=ROOT/oe
    nodes=(loadj(vn) if vn.is_file() else []) + (loadj(bn) if bn.is_file() else [])
    edges=(loadj(ve) if ve.is_file() else []) + (loadj(be) if be.is_file() else [])
    extra_nodes=[]; extra_edges=[]
    for n in nodes[:200]:
        src=str(n.get('node_id',''))
        if not src: continue
        for t in list(n.get('theme_tags') or [])[:1]:
            tid=f'theme::{t}'; extra_nodes.append({'schema':'bible_meaning_graph_node_v1','node_id':tid,'kind':'theme','label':t}); extra_edges.append({'schema':'bible_meaning_graph_edge_v1','src_node_id':src,'dst_node_id':tid,'edge_type':'theme_association','weight':0.6})
        for r in list(n.get('regime_tags') or [])[:1]:
            rid=f'regime::{r}'; extra_nodes.append({'schema':'bible_meaning_graph_node_v1','node_id':rid,'kind':'regime','label':r}); extra_edges.append({'schema':'bible_meaning_graph_edge_v1','src_node_id':src,'dst_node_id':rid,'edge_type':'regime_projection','weight':0.6})
    on.parent.mkdir(parents=True, exist_ok=True); oe.parent.mkdir(parents=True, exist_ok=True)
    on.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in (nodes+extra_nodes))+'\n', encoding='utf-8')
    oe.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in (edges+extra_edges))+'\n', encoding='utf-8')
    print(str(on)); print(str(oe)); return 0
if __name__=='__main__': raise SystemExit(main())
