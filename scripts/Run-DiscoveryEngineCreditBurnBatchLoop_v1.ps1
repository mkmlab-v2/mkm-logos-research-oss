# Discovery Engine credit burn — multi-batch loop (detached-friendly).
param(
    [int]$BatchCount = 20,
    [int]$QueriesPerBatch = 500,
    [int]$StartBatch = 1
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Log = Join-Path $Root 'reports\de_credit_burn_batch_loop_v1.log'
$Summary = Join-Path $Root 'reports\de_credit_burn_loop_summary_v1.json'

function Write-LoopLog([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -Path $Log -Value $line -Encoding UTF8
    Write-Host $line
}

$endBatch = $StartBatch + $BatchCount - 1
Write-LoopLog "LOOP START batch_count=$BatchCount queries_per_batch=$QueriesPerBatch range=$StartBatch..$endBatch"

$ok = 0
$fail = 0
for ($i = $StartBatch; $i -le $endBatch; $i++) {
    Write-LoopLog "BATCH $i / $endBatch begin"
    & py scripts/run_discovery_engine_app_builder_credit_burn_v1.py `
        --query-count $QueriesPerBatch `
        --compact `
        --no-update-probe
    if ($LASTEXITCODE -ne 0) {
        $fail++
        Write-LoopLog "BATCH $i FAIL exit=$LASTEXITCODE"
        continue
    }
    $ok++
    Write-LoopLog "BATCH $i OK"
}

Write-LoopLog "ALL $BatchCount BATCHES DONE (range $StartBatch..$endBatch ok=$ok fail=$fail)"

$summary = @{
    schema                   = 'de_credit_burn_loop_summary_v1'
    generated_at_utc         = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    project_id               = 'mkm-lab-agi-2025'
    engine_id                = 'b2g-search-mkm-lab-agi-2025'
    log_path                 = 'reports/de_credit_burn_batch_loop_v1.log'
    loop                     = @{
        batch_count       = $BatchCount
        queries_per_batch = $QueriesPerBatch
        start_batch       = $StartBatch
        end_batch         = $endBatch
        batches_ok        = $ok
        batches_fail      = $fail
        completed_local   = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        status            = if ($fail -eq 0) { 'ALL_BATCHES_DONE' } else { 'DONE_WITH_FAILURES' }
    }
    billing_surface          = 'discovery_engine'
    follow_up                = 'Billing > Credits (authuser=1) + Reports Discovery Engine SKU after 24-48h'
}
$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $Summary -Encoding UTF8
