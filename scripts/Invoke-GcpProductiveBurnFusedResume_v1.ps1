# Fused GCP productive burn resume: P3 done (IAM-blocked) -> auth jema12 -> P4 post-IAM deploy.
param(
    [string]$Project = "gen-lang-client-0846393371",
    [string]$RequiredAccount = "jema12@mkmlife.com",
    [string]$ConfigName = "mkm-genlang-burn",
    [switch]$SkipAuthLogin,
    [switch]$PostIamWave,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Completion = Join-Path $Root "reports/gcp_productive_burn_completion_v1_latest.json"
$Deploy = Join-Path $Root "reports/gcp_productive_burn_deploy_status_v1_latest.json"
$Handoff = Join-Path $Root "reports/gcp_productive_burn_fused_handoff_v1_latest.json"
$Auto = Join-Path $Root "scripts/Invoke-GcpProductiveBurnCloudShellAuto_v1.ps1"

function Get-GcloudAccounts {
    @(gcloud auth list --format="value(account)" 2>$null | Where-Object { $_ })
}

Write-Host "=== GCP productive burn fused resume [HYPO] ==="
Write-Host "P3: rows full, calls_ok=0 (IAM). PostIamWave=$PostIamWave"

$accounts = Get-GcloudAccounts
$hasJema = $accounts -contains $RequiredAccount
$active = (gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null | Select-Object -First 1)

$handoffPreview = [ordered]@{
    schema               = "gcp_productive_burn_fused_handoff_v1"
    generated_at_utc     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hypothesis_tag       = "[HYPO]"
    mode                 = "productive_burn_btrack_research_only"
    phase_p3             = @{
        status       = "lanes_done_iam_blocked"
        asset_rag    = "600/600 rows, calls_ok=0"
        btrack_fills = "200/200 rows, calls_ok=0"
        local_pull   = "reports/sandbox/gcp_productive_burn_logs/"
    }
    phase_p4             = @{
        trigger = "IAM Vertex AI User on $Project for $RequiredAccount"
        wave    = "P4a_genlang + P4b_fills"
        note    = "Fresh jsonl — P3 archived; do not resume at index 601"
    }
    gcloud               = @{
        required_account = $RequiredAccount
        active_account   = $active
        jema12_present   = $hasJema
        project          = $Project
        config_name      = $ConfigName
    }
    sibling_lanes_hold   = @{
        MS340          = "PMS human"
        fills_prophecy = "wait new Binance fill"
        multi_res      = "routine ok 1669 rows"
        gitea_main     = "e5fda700d7 merged"
    }
    next_command         = "powershell -File scripts\Invoke-GcpProductiveBurnFusedResume_v1.ps1 -PostIamWave"
}
($handoffPreview | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $Handoff -Encoding utf8
Write-Host "handoff: $Handoff"

if (-not $hasJema) {
    if ($SkipAuthLogin -or $DryRun) {
        Write-Host "BLOCK: $RequiredAccount not in gcloud auth list. Run: gcloud auth login $RequiredAccount"
        if (-not $DryRun) { exit 2 }
    }
    else {
        Write-Host "Opening browser OAuth for $RequiredAccount ..."
        & gcloud auth login $RequiredAccount --brief
        if ($LASTEXITCODE -ne 0) { throw "gcloud auth login failed (exit $LASTEXITCODE)" }
        $hasJema = $true
    }
}

if (-not $DryRun) {
    $cfgList = gcloud config configurations list --format="value(name)" 2>$null
    if ($cfgList -notcontains $ConfigName) {
        & gcloud config configurations create $ConfigName --no-activate 2>$null
    }
    & gcloud config configurations activate $ConfigName
    & gcloud config set account $RequiredAccount
    & gcloud config set project $Project
    $active = $RequiredAccount
}

if ($DryRun) {
    Write-Host "DryRun OK — complete OAuth + IAM then rerun with -PostIamWave"
    exit 0
}

if (-not $PostIamWave) {
    Write-Host @"

FUSED GATE (human 1x before -PostIamWave):
  1) GCP Console ($RequiredAccount) -> IAM -> Vertex AI User on $Project
  2) Rerun: powershell -File scripts\Invoke-GcpProductiveBurnFusedResume_v1.ps1 -PostIamWave

"@
    exit 0
}

& $Auto -Project $Project -RequiredAccount $RequiredAccount -PostIamWave
exit $LASTEXITCODE
