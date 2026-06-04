# Golden-40 distributed chain + infra probes (research_only)
param(
    [switch]$MainOnly,
    [switch]$Auto,
    [switch]$LocalBothShards,
    [switch]$StagingMergeLocalShard1,
    [switch]$PublishLocalShard1ToShare,
    [switch]$SkipAuxDeploy,
    [switch]$ProbeP1,
    [string]$AuxIp = "180.224.2.24",
    [string]$AuxHost = "DESKTOP-AP1DC83",
    [string]$ShareRoot = "Z:\nextgen_cpu_aux",
    [int]$AutoWaitSec = 90
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

if ($Auto -or $MainOnly) {
    $autoArgs = @("scripts/run_nextgen_aux_automation_chain_v1.py")
    if ($MainOnly) {
        $autoArgs += "--main-only"
    } else {
        $autoArgs += @(
            "--aux-ip", $AuxIp,
            "--aux-host", $AuxHost,
            "--share-root", $ShareRoot,
            "--wait-sec", "$AutoWaitSec"
        )
        if ($SkipAuxDeploy) { $autoArgs += "--skip-deploy" }
    }
    py @autoArgs
    exit $LASTEXITCODE
}

if (-not $SkipAuxDeploy) {
    py scripts/deploy_nextgen_clean_slate_cpu_aux_drop_v1.py --share-root $ShareRoot --merge-only
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

py scripts/run_nextgen_golden40_distributed_readiness_v1.py --aux-ip $AuxIp --share-root $ShareRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$argsList = @("scripts/run_nextgen_ng40_golden40_distributed_chain_v1.py")
if ($LocalBothShards) { $argsList += "--local-both-shards" }
if ($StagingMergeLocalShard1) { $argsList += "--staging-merge-local-shard1" }
if ($PublishLocalShard1ToShare) { $argsList += "--publish-local-shard1-to-share" }
py @argsList
$chainRc = $LASTEXITCODE

if ($ProbeP1) {
    py scripts/run_nextgen_p1_aux_distributed_chain_v1.py --aux-ip $AuxIp --rounds 3
}

exit $chainRc
