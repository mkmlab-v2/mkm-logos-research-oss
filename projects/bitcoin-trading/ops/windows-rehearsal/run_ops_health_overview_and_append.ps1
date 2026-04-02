param(
    [string]$OverviewScriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\build_ops_health_overview.ps1",
    [string]$AppendScriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\append_ops_loop_snapshot.ps1",
    [string]$FactBriefScriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\generate_ops_fact_brief.ps1",
    [string]$LoopMarkdownPath = "C:\workspace\docs\final\artifacts\OPS_NOTEBOOK_DRIVEN_LOOP_2026-04-02_2245.md",
    [string]$OpsOverviewJsonPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\ops_health_overview_latest.json",
    [string]$PublicStatusRemote = "root@148.230.97.246:/var/www/jemaai/ops_health_overview_latest.json",
    [switch]$SkipPublishPublicStatus
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $OverviewScriptPath)) {
    throw "Missing overview script: $OverviewScriptPath"
}
if (-not (Test-Path -LiteralPath $AppendScriptPath)) {
    throw "Missing append script: $AppendScriptPath"
}
if (-not (Test-Path -LiteralPath $FactBriefScriptPath)) {
    throw "Missing fact brief script: $FactBriefScriptPath"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $OverviewScriptPath
if ($LASTEXITCODE -ne 0) {
    throw "Overview build failed. ExitCode=$LASTEXITCODE"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $AppendScriptPath -TargetMarkdownPath $LoopMarkdownPath
if ($LASTEXITCODE -ne 0) {
    throw "Append snapshot failed. ExitCode=$LASTEXITCODE"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $FactBriefScriptPath
if ($LASTEXITCODE -ne 0) {
    throw "Fact brief generation failed. ExitCode=$LASTEXITCODE"
}

if (-not $SkipPublishPublicStatus) {
    if (-not (Test-Path -LiteralPath $OpsOverviewJsonPath)) {
        throw "Ops overview json not found: $OpsOverviewJsonPath"
    }
    & scp "$OpsOverviewJsonPath" "$PublicStatusRemote"
    if ($LASTEXITCODE -ne 0) {
        throw "Public status publish failed. ExitCode=$LASTEXITCODE"
    }
}

Write-Host "OK overview build + loop snapshot append + fact brief (+ public status publish) completed"
