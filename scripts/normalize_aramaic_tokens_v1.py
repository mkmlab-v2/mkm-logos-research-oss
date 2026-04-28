#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]

def _norm(text:str)->str:
    s=str(text).lower().replace('/', ' ')
    s=re.sub(r"[\u0591-\u05C7]", "", s)
    return re.sub(r"\s+", " ", s).strip()

def _tags(verse_id:str)->tuple[list[str],list[str]]:
    b=verse_id.split('.')[0].lower()
    if 'dan' in b: return ['imperial_transition'], ['empire_transition']
    if 'ezra' in b: return ['restoration_decree'], ['return_cycle']
    return ['warning_oracle'], ['stress_signal']

def _load_jsonl(path:Path)->list[dict[str,Any]]:
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
    if not inp.is_file(): raise SystemExit(f'missing input jsonl: {inp}')
    rows=_load_jsonl(inp); out_rows=[]
    for r in rows:
        vid=str(r.get('verse_id','')).strip(); txt=str(r.get('text') or r.get('verse_text') or r.get('content') or '')
        if not vid or not txt: continue
        th,rg=_tags(vid); n=dict(r)
        n['text_norm']=_norm(txt)
        n['theme_tags']=n.get('theme_tags') or th
        n['regime_tags']=n.get('regime_tags') or rg
        n['time_bucket']=n.get('time_bucket') or 'ancient_empire_cycle'
        out_rows.append(n)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out_rows)+'\n', encoding='utf-8')
    print(str(out)); return 0
if __name__=='__main__': raise SystemExit(main())
