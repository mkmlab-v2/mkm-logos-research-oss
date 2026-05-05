#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
W={'timeline_anchor':0.18,'causal_precursor':0.17,'fulfillment':0.16,'recurrence':0.16,'contrast_inversion':0.14,'cross_lens_confirm':0.19}

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
    ap=argparse.ArgumentParser(); ap.add_argument('--edges-jsonl', required=True); ap.add_argument('--bridge-edges-jsonl'); ap.add_argument('--include-bridge-edges', action='store_true'); ap.add_argument('--bridge-lang-coef-json'); ap.add_argument('--insight-json'); ap.add_argument('--survivor-json'); ap.add_argument('--include-insight-signal', action='store_true'); ap.add_argument('--mid-vol-threshold', type=float, default=0.2); ap.add_argument('--high-vol-threshold', type=float, default=0.4); ap.add_argument('--insight-max-delta-low-vol', type=float, default=0.06); ap.add_argument('--insight-max-delta-mid-vol', type=float, default=0.045); ap.add_argument('--insight-max-delta-high-vol', type=float, default=0.03); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    ep=Path(a.edges_jsonl); bp=Path(a.bridge_edges_jsonl) if a.bridge_edges_jsonl else None; op=Path(a.output_json)
    if not ep.is_absolute(): ep=ROOT/ep
    if bp and not bp.is_absolute(): bp=ROOT/bp
    if not op.is_absolute(): op=ROOT/op
    edges=loadj(ep)
    if a.include_bridge_edges and bp and bp.is_file(): edges.extend(loadj(bp))
    if not edges: raise SystemExit('no edges to score')
    total=0.0; mass=0.0
    for e in edges:
        t=str(e.get('edge_type','')); w=float(W.get(t,0.05)); c=float(e.get('confidence',0.5)); total+=w*c; mass+=w
    base=total/max(mass,1e-9)
    overlap=sum(float(e.get('semantic_overlap',0.0)) for e in edges)/max(len(edges),1)
    conflict=max(0.0,min(1.0,1.0-overlap))
    signal=0.5 if a.include_insight_signal else 0.0
    if conflict>=a.high_vol_threshold: cap=a.insight_max_delta_high_vol; bucket='high_vol'
    elif conflict>=a.mid_vol_threshold: cap=a.insight_max_delta_mid_vol; bucket='mid_vol'
    else: cap=a.insight_max_delta_low_vol; bucket='low_vol'
    delta=min(cap,max(0.0,signal*cap)); score=max(0.0,min(1.0,base+delta))
    label='alert' if score>=0.7 else ('watch' if score>=0.5 else 'stable')
    doc={'schema':'aramaic_regime_shift_score_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','edge_count':len(edges),'conflict_ratio':round(conflict,6),'insight_signal':round(signal,6),'insight_signal_applied':bool(a.include_insight_signal),'insight_delta_applied':round(delta,6),'insight_cap_bucket':bucket,'shift_score':round(score,6),'signal_label':label}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
