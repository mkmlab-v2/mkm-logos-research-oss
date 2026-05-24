#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel Track C commercialization (B2B pack + graph-wire PoC + showroom deploy/smoke).
  MS paste pack excluded.
#>
$ErrorActionPreference = "Stop"
$root = "c:\workspace"
Set-Location $root

function Invoke-Step {
    param([string]$Name, [scriptblock]$Block)
    Write-Host "== START $Name ==" -ForegroundColor Cyan
    & $Block
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Host "== FAIL $Name exit=$code ==" -ForegroundColor Red
        exit $code
    }
    Write-Host "== OK $Name ==" -ForegroundColor Green
}

$jobs = @(
    @{
        Name = "b2b_meeting_pack"
        Block = {
            py scripts/build_track_c_b2b_meeting_pack_v1.py --skip-commander
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            py scripts/check_track_c_b2b_meeting_pack_readiness_v1.py
        }
    },
    @{
        Name = "graph_wire_rag_poc"
        Block = {
            py scripts/build_mkm_graph_wire_rag_poc_v1.py
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            py -m pytest tests/test_build_mkm_graph_wire_rag_poc_v1.py -q
        }
    },
    @{
        Name = "showroom_commercial_slice"
        Block = {
            py scripts/publish_logos_chronology_dynamic_map_showroom_v1.py
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            py scripts/build_showroom_meaning_topology_graph_slice_v1.py --seed-count 14 --max-nodes 72 --max-edges 140
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            py scripts/build_showroom_meaning_topology_qa_presets_v1.py
        }
    }
)

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }

$psJobs = foreach ($j in $jobs) {
    Start-Job -Name $j.Name -ScriptBlock {
        param($Root, $Py, $Name)
        Set-Location $Root
        $ErrorActionPreference = "Stop"
        function Invoke-PyStep([string]$Label, [string[]]$Args) {
            Write-Output "[$Name] + $Py $($Args -join ' ')"
            & $Py @Args
            if ($LASTEXITCODE -ne 0) {
                throw "$Label failed exit=$LASTEXITCODE"
            }
        }
        switch ($Name) {
            "b2b_meeting_pack" {
                Invoke-PyStep "b2b_pack" @("scripts/build_track_c_b2b_meeting_pack_v1.py", "--skip-commander")
                Invoke-PyStep "b2b_readiness" @("scripts/check_track_c_b2b_meeting_pack_readiness_v1.py")
            }
            "graph_wire_rag_poc" {
                Invoke-PyStep "graph_wire_poc" @("scripts/build_mkm_graph_wire_rag_poc_v1.py")
                Invoke-PyStep "graph_wire_pytest" @("-m", "pytest", "tests/test_build_mkm_graph_wire_rag_poc_v1.py", "-q")
            }
            "showroom_commercial_slice" {
                Invoke-PyStep "dynamic_map" @("scripts/publish_logos_chronology_dynamic_map_showroom_v1.py")
                Invoke-PyStep "graph_slice" @(
                    "scripts/build_showroom_meaning_topology_graph_slice_v1.py",
                    "--seed-count", "14", "--max-nodes", "72", "--max-edges", "140"
                )
                Invoke-PyStep "qa_presets" @("scripts/build_showroom_meaning_topology_qa_presets_v1.py")
            }
            default { throw "unknown job $Name" }
        }
    } -ArgumentList $root, $py, $j.Name
}

$failed = @()
$psJobs | Wait-Job | ForEach-Object {
    $job = $_
    $recvErr = $null
    $out = Receive-Job -Job $job -ErrorVariable recvErr -ErrorAction SilentlyContinue
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($recvErr) {
        $recvErr | ForEach-Object { Write-Host "[$($job.Name)] Receive-Job error: $_" -ForegroundColor Red }
    }
    $reason = $null
    if ($job.ChildJobs -and $job.ChildJobs.Count -gt 0) {
        $reason = $job.ChildJobs[0].JobStateInfo.Reason
    }
    if ($job.State -ne "Completed" -or $reason) {
        $failed += $job.Name
        Write-Host "== FAIL job $($job.Name) state=$($job.State) reason=$reason ==" -ForegroundColor Red
    }
}
$psJobs | Remove-Job -Force -ErrorAction SilentlyContinue
if ($failed.Count -gt 0) {
    Write-Host "Parallel jobs failed: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}

Invoke-Step "deploy_vps" {
    powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_showroom_to_vps.ps1
}

Invoke-Step "gates" {
    py scripts/check_showroom_trust_viz_public_chain_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    py -m pytest tests/test_logos_trace_api_stub_v1.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    py scripts/build_logos_observatory_commercial_readiness_v1.py
}

Write-Host "Parallel commercialization complete." -ForegroundColor Green
