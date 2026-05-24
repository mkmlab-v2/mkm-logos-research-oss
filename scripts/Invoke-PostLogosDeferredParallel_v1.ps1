#Requires -Version 5.1
<#
.SYNOPSIS
  POST-LOGOS-COMMERCIAL-GRADE deferred parallel: DF-P0-02 + MS-PASTE + O-P5 prep.
  MS∩Logos: paste has no Logos compression FinOps claims; O-P5 human SSH remains.
#>
$ErrorActionPreference = "Stop"
$root = "c:\workspace"
Set-Location $root

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }

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
        Name = "df_p0_02"
        Block = {
            param($Root, $Py)
            Set-Location $Root
            & $Py scripts/build_mkm_graph_wire_rag_poc_v1.py
            if ($LASTEXITCODE -ne 0) { throw "poc build exit=$LASTEXITCODE" }
            & $Py -m pytest tests/test_build_mkm_graph_wire_rag_poc_v1.py -q
            if ($LASTEXITCODE -ne 0) { throw "poc pytest exit=$LASTEXITCODE" }
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1
            if ($LASTEXITCODE -ne 0) { throw "p0 verify exit=$LASTEXITCODE" }
        }
    },
    @{
        Name = "ms_paste_pack"
        Block = {
            param($Root, $Py)
            Set-Location $Root
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MsRq019PastePackReadiness_v1.ps1
            if ($LASTEXITCODE -ne 0) { throw "paste readiness exit=$LASTEXITCODE" }
        }
    },
    @{
        Name = "op5_prep"
        Block = {
            param($Root, $Py)
            Set-Location $Root
            $ErrorActionPreference = "Continue"
            foreach ($script in @(
                "scripts/verify_jema12_studio_oracle_redirect_v1.py",
                "scripts/verify_jema_ai_studio_oracle_bridge_v1.py"
            )) {
                if (-not (Test-Path -LiteralPath $script)) { continue }
                & $Py $script
                Write-Output "[$script] exit=$LASTEXITCODE (warn-only)"
            }
        }
    },
    @{
        Name = "df_p1_04_registry"
        Block = {
            param($Root, $Py)
            Set-Location $Root
            & $Py scripts/bootstrap_data_fabric_module_registry_v1.py
            if ($LASTEXITCODE -ne 0) { throw "registry bootstrap exit=$LASTEXITCODE" }
        }
    }
)

$psJobs = foreach ($j in $jobs) {
    Start-Job -Name $j.Name -ScriptBlock $j.Block -ArgumentList $root, $py
}

$failed = @()
$psJobs | Wait-Job | ForEach-Object {
    $job = $_
    $recvErr = $null
    $out = Receive-Job -Job $job -ErrorVariable recvErr -ErrorAction SilentlyContinue
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($recvErr) {
        $recvErr | ForEach-Object { Write-Host "[$($job.Name)] $_" -ForegroundColor Yellow }
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
    Write-Host "Deferred parallel failed: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host "POST-DEFERRED parallel complete (DF-P0-02 + MS-PASTE + O-P5 probes)." -ForegroundColor Green
exit 0
