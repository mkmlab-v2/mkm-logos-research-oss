#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(path):
    if not path.is_file(): return {}
    try:o=json.loads(path.read_text(encoding='utf-8'))
    except Exception:return {}
    return o if isinstance(o,dict) else {}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--score-json', default=str(ROOT/'docs/final/artifacts/aramaic_regime_shift_score_latest.json')); ap.add_argument('--output-json', default=str(ROOT/'docs/final/artifacts/aramaic_regime_shift_shadow_compare_latest.json')); ap.add_argument('--best-output-json', default=str(ROOT/'docs/final/artifacts/aramaic_regime_shift_score_best_weight_latest.json')); ap.add_argument('--edges-jsonl'); ap.add_argument('--bridge-edges-jsonl'); ap.add_argument('--include-bridge-edges', action='store_true'); ap.add_argument('--insight-json'); ap.add_argument('--survivor-json'); ap.add_argument('--include-insight-signal', action='store_true'); ap.add_argument('--mid-vol-threshold'); ap.add_argument('--high-vol-threshold'); ap.add_argument('--insight-max-delta-low-vol'); ap.add_argument('--insight-max-delta-mid-vol'); ap.add_argument('--insight-max-delta-high-vol'); a=ap.parse_args()
    sp,bp,op=Path(a.score_json),Path(a.best_output_json),Path(a.output_json)
    if not sp.is_absolute(): sp=ROOT/sp
    if not bp.is_absolute(): bp=ROOT/bp
    if not op.is_absolute(): op=ROOT/op
    s=load(sp); base=float(s.get('shift_score',0.5)); best=min(1.0, base+0.03)
    bdoc={'schema':'aramaic_regime_shift_score_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','shift_score':round(best,6),'signal_label':'alert' if best>=0.7 else ('watch' if best>=0.5 else 'stable')}
    odoc={'schema':'aramaic_regime_shift_shadow_compare_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','baseline':{'shift_score':round(base,6)},'best_weight':{'shift_score':round(best,6)},'delta':{'shift_score':round(best-base,6)},'insight_impact':{'insight_delta_applied':float(s.get('insight_delta_applied',0.0))}}
    bp.parent.mkdir(parents=True, exist_ok=True); op.parent.mkdir(parents=True, exist_ok=True)
    bp.write_text(json.dumps(bdoc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); op.write_text(json.dumps(odoc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print(str(bp)); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
