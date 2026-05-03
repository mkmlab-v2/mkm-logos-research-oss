<#

.SYNOPSIS

  Run Track C plan gates smoke (bundle verify + orchestrator pytest) and append one JSON line to reports.



.DESCRIPTION

  Exit code is propagated from run_trackc_plan_gates_smoke_v1.py. Log: reports/trackc_plan_gates_smoke_run_log.jsonl

#>

param(

    [string]$WorkspaceRoot = "C:\workspace"

)



$ErrorActionPreference = "Stop"

$py = Join-Path $WorkspaceRoot "scripts\run_trackc_plan_gates_smoke_v1.py"

if (-not (Test-Path -LiteralPath $py)) { throw "Not found: $py" }



$reports = Join-Path $WorkspaceRoot "reports"

if (-not (Test-Path -LiteralPath $reports)) {

    New-Item -ItemType Directory -Path $reports -Force | Out-Null

}

$log = Join-Path $reports "trackc_plan_gates_smoke_run_log.jsonl"



& py $py --workspace-root $WorkspaceRoot

$code = $LASTEXITCODE



$line = (@{

    schema     = "trackc_plan_gates_smoke_run_v1"

    ts_utc     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    exit_code  = $code

} | ConvertTo-Json -Compress)



Add-Content -LiteralPath $log -Value $line -Encoding utf8

exit $code

