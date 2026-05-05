#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(p):
    o=json.loads(p.read_text(encoding='utf-8'))
    return o if isinstance(o,dict) else {}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--audience-pack-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    ip,op=Path(a.audience_pack_json),Path(a.output_json)
    if not ip.is_absolute(): ip=ROOT/ip
    if not op.is_absolute(): op=ROOT/op
    d=load(ip); variants=list(d.get('variants') or [])
    n60=[]; n180=[]
    for v in variants:
        aud=v.get('audience','general')
        n60.append({'audience':aud,'seconds':60,'script':f'{aud}: two-track safety-gated summary'})
        n180.append({'audience':aud,'seconds':180,'script':f'{aud}: expanded two-track method, evidence, and boundary'})
    out={'schema':'two_track_presenter_notes_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','notes_60s':n60,'notes_180s':n180}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
