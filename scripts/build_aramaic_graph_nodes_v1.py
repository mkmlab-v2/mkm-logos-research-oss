#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]

def loadj(path: Path)->list[dict[str,Any]]:
    out=[]
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        s=line.strip()
        if not s: continue
        try:o=json.loads(s)
        except Exception: continue
        if isinstance(o,dict): out.append(o)
    return out

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--input-jsonl', required=True); ap.add_argument('--output-jsonl', required=True); a=ap.parse_args()
    inp=Path(a.input_jsonl); out=Path(a.output_jsonl)
    if not inp.is_absolute(): inp=ROOT/inp
    if not out.is_absolute(): out=ROOT/out
    rows=loadj(inp)
    nodes=[]
    for r in rows:
        ref=str(r.get('verse_id') or r.get('source_ref') or '').strip(); txt=str(r.get('text_norm') or '').strip()
        if not ref or not txt: continue
        nodes.append({'schema':'aramaic_graph_node_v1','node_id':f'aramaic::{ref}','corpus':'aramaic','ref':ref,'text_norm':txt,'time_bucket':str(r.get('time_bucket') or 'ancient_empire_cycle'),'theme_tags':list(r.get('theme_tags') or []),'regime_tags':list(r.get('regime_tags') or []),'research_only':True,'promotion_required':True,'source_track':'B'})
    nodes.sort(key=lambda x:x['ref'])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(json.dumps(n,ensure_ascii=False) for n in nodes)+'\n', encoding='utf-8')
    print(str(out)); return 0
if __name__=='__main__': raise SystemExit(main())
