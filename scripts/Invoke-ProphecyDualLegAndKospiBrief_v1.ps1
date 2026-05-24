#Requires -Version 5.1
<#
.SYNOPSIS
  Build dual-leg prophecy brief + internal KOSPI morning onepager from existing score JSON.

.DESCRIPTION
  Expects docs/final/artifacts/btrack_prophecy_score_latest.json (from daily eval).
  Does not rebuild score. B-track / research_only.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$scoreJson = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_latest.json"
if (-not (Test-Path -LiteralPath $scoreJson)) {
    throw "Missing score JSON (run eval chain first): $scoreJson"
}

$wsPy = ($WorkspaceRoot.TrimEnd('\') -replace '\\', '/')
$splitScript = @'
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("__WORKSPACE_ROOT__")
src = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
doc = json.loads(src.read_text(encoding="utf-8"))
rows = doc.get("rows") or []

def leg(tag):
    xs = [r for r in rows if r.get("instrument") == tag]
    n = len(xs)
    hits = sum(1 for r in xs if r.get("predicted_direction") == r.get("actual_direction"))
    return {
        "instrument": tag,
        "n_evaluated": n,
        "price_hits": hits,
        "price_directional_hit_rate": round(hits / n, 6) if n else None,
    }

def write_score(path, subset_rows, note):
    out_doc = dict(doc)
    out_doc["rows"] = subset_rows
    meta = dict(doc.get("meta") or {})
    meta["filter_note"] = note
    out_doc["meta"] = meta
    path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

kospi_rows = [r for r in rows if r.get("instrument") == "kospi"]
btc_rows = [r for r in rows if r.get("instrument") == "btc"]

kospi_score = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_kospi_only_latest.json"
btc_score = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_btc_only_latest.json"
cmp_json = ROOT / "docs" / "final" / "artifacts" / "prophecy_hit_rate_dual_leg_comparison_latest.json"

write_score(kospi_score, kospi_rows, "instrument==kospi only")
write_score(btc_score, btc_rows, "instrument==btc only")

k = leg("kospi")
b = leg("btc")
dk = None
if k["price_directional_hit_rate"] is not None and b["price_directional_hit_rate"] is not None:
    dk = round(b["price_directional_hit_rate"] - k["price_directional_hit_rate"], 6)

cmp_payload = {
    "schema": "prophecy_hit_rate_dual_leg_comparison_v1",
    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "research_only": True,
    "zeroing_note": "Same frozen hypothesis direction vs each leg OHLCV; not live trading.",
    "source": {
        "score_build": "docs/final/artifacts/btrack_prophecy_score_latest.json",
        "hypothesis": doc.get("hypothesis_path", ""),
    },
    "window": {
        "recent_trading_days": (doc.get("inputs") or {}).get("recent_trading_days"),
        "batch_eval_dates": (doc.get("meta") or {}).get("batch_eval_dates"),
    },
    "legs": {"kospi": k, "btc": b},
    "delta": {"btc_minus_kospi_hit_rate": dk},
}
cmp_json.write_text(json.dumps(cmp_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"WROTE: {kospi_score}")
print(f"WROTE: {btc_score}")
print(f"WROTE: {cmp_json}")
'@

$splitScriptResolved = $splitScript.Replace("__WORKSPACE_ROOT__", $wsPy)
$splitTmp = Join-Path $env:TEMP ("dual_leg_split_" + [guid]::NewGuid().ToString("n") + ".py")
try {
    Set-Content -LiteralPath $splitTmp -Value $splitScriptResolved -Encoding UTF8
    & py $splitTmp
    if ($LASTEXITCODE -ne 0) { throw "dual-leg split exit $LASTEXITCODE" }
}
finally {
    Remove-Item -LiteralPath $splitTmp -Force -ErrorAction SilentlyContinue
}

$kospiScore = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_kospi_only_latest.json"
$btcScore = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_btc_only_latest.json"
$kospiEvalOut = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_kospi_only_latest.json"
$btcEvalOut = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_btc_only_latest.json"

Write-Host "==> eval_prophecy_hit_rate_v1.py (KOSPI-only)" -ForegroundColor Cyan
& py "scripts\eval_prophecy_hit_rate_v1.py" "--run-mode" "price" "--score-json" $kospiScore "--output" $kospiEvalOut
if ($LASTEXITCODE -ne 0) { throw "KOSPI-only eval exit $LASTEXITCODE" }

Write-Host "==> eval_prophecy_hit_rate_v1.py (BTC-only)" -ForegroundColor Cyan
& py "scripts\eval_prophecy_hit_rate_v1.py" "--run-mode" "price" "--score-json" $btcScore "--output" $btcEvalOut
if ($LASTEXITCODE -ne 0) { throw "BTC-only eval exit $LASTEXITCODE" }

$briefScript = @'
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("__WORKSPACE_ROOT__")
art = ROOT / "docs" / "final" / "artifacts"
overall = json.loads((art / "prophecy_hit_rate_eval_latest.json").read_text(encoding="utf-8"))
kospi = json.loads((art / "prophecy_hit_rate_eval_kospi_only_latest.json").read_text(encoding="utf-8"))
btc = json.loads((art / "prophecy_hit_rate_eval_btc_only_latest.json").read_text(encoding="utf-8"))
cmp_ = json.loads((art / "prophecy_hit_rate_dual_leg_comparison_latest.json").read_text(encoding="utf-8"))

def m(doc):
    mm = doc.get("metrics") or {}
    return {
        "price_directional_hit_rate": mm.get("price_directional_hit_rate"),
        "n_evaluated": mm.get("n_evaluated"),
        "price_hits": mm.get("price_hits"),
    }

payload = {
    "schema": "trackc_prophecy_dual_leg_brief_v1",
    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "research_only": True,
    "window": {"recent_trading_days": ((cmp_.get("window") or {}).get("recent_trading_days"))},
    "overall": m(overall),
    "legs": {"kospi": m(kospi), "btc": m(btc)},
    "delta": cmp_.get("delta") or {},
    "sources": {
        "overall_eval": "docs/final/artifacts/prophecy_hit_rate_eval_latest.json",
        "kospi_eval": "docs/final/artifacts/prophecy_hit_rate_eval_kospi_only_latest.json",
        "btc_eval": "docs/final/artifacts/prophecy_hit_rate_eval_btc_only_latest.json",
        "dual_compare": "docs/final/artifacts/prophecy_hit_rate_dual_leg_comparison_latest.json",
    },
}

brief_json = art / "trackc_prophecy_dual_leg_brief_latest.json"
brief_md = art / "trackc_prophecy_dual_leg_brief_latest.md"
brief_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def pct(v):
    if v is None:
        return "n/a"
    return f"{v*100:.2f}%"

md = [
    "# Track C Prophecy Dual-Leg Brief",
    "",
    f"- generated_at_utc: `{payload['generated_at_utc']}`",
    f"- recent_trading_days: `{payload['window']['recent_trading_days']}`",
    f"- overall_hit_rate: `{pct(payload['overall']['price_directional_hit_rate'])}` ({payload['overall']['price_hits']}/{payload['overall']['n_evaluated']})",
    f"- kospi_hit_rate: `{pct(payload['legs']['kospi']['price_directional_hit_rate'])}` ({payload['legs']['kospi']['price_hits']}/{payload['legs']['kospi']['n_evaluated']})",
    f"- btc_hit_rate: `{pct(payload['legs']['btc']['price_directional_hit_rate'])}` ({payload['legs']['btc']['price_hits']}/{payload['legs']['btc']['n_evaluated']})",
    f"- btc_minus_kospi_hit_rate: `{payload['delta'].get('btc_minus_kospi_hit_rate')}`",
    "",
    "> research_only: measurement snapshot, not a live trading trigger.",
]
brief_md.write_text("\n".join(md) + "\n", encoding="utf-8")
print(f"WROTE: {brief_json}")
print(f"WROTE: {brief_md}")
'@

$briefScriptResolved = $briefScript.Replace("__WORKSPACE_ROOT__", $wsPy)
$briefTmp = Join-Path $env:TEMP ("dual_leg_brief_" + [guid]::NewGuid().ToString("n") + ".py")
try {
    Set-Content -LiteralPath $briefTmp -Value $briefScriptResolved -Encoding UTF8
    & py $briefTmp
    if ($LASTEXITCODE -ne 0) { throw "dual-leg brief exit $LASTEXITCODE" }
}
finally {
    Remove-Item -LiteralPath $briefTmp -Force -ErrorAction SilentlyContinue
}

Write-Host "==> build_internal_kospi_morning_brief_onepager_v1.py" -ForegroundColor Cyan
& py "scripts\build_internal_kospi_morning_brief_onepager_v1.py"
if ($LASTEXITCODE -ne 0) { throw "morning brief exit $LASTEXITCODE" }

Write-Host "[OK] Dual-leg brief + KOSPI morning onepager refreshed." -ForegroundColor Green
