# Exit 0 when biblical_single_lane_trading_hook live_trading.allowed is true; else 1.
# Hook path: memory/v2/ops/biblical_single_lane_trading_hook_v1_latest.json (sync from workspace).

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$btRoot = (Get-Item -LiteralPath (Join-Path $here "..\..\..")).FullName
$hook = Join-Path $btRoot "memory\v2\ops\biblical_single_lane_trading_hook_v1_latest.json"

if (-not (Test-Path -LiteralPath $hook)) {
    Write-Host "[biblical-lane] missing hook: $hook (run Sync-BiblicalLaneHook.ps1 or stability check with -SyncBitcoinTradingHook)"
    exit 2
}
$j = Get-Content -LiteralPath $hook -Raw -Encoding utf8 | ConvertFrom-Json
$lt = $j.live_trading
if ($null -eq $lt) {
    Write-Host "[biblical-lane] live_trading missing in hook JSON"
    exit 3
}
if ([bool]$lt.allowed) {
    Write-Host ("[biblical-lane] OK instrument={0} phase={1}" -f $j.instrument, $lt.phase)
    exit 0
}
Write-Host ("[biblical-lane] BLOCKED phase={0}" -f $lt.phase)
foreach ($r in @($lt.reasons_if_blocked)) { Write-Host ("  - {0}" -f $r) }
exit 1
