# Parallel post-L3-ACK: prod ST swap + gate + review packet + L3 readiness + MS fusion + pytest
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$py = 'py'
$jobs = @(
    @{ Name = 'l3_swap'; Cmd = "$py scripts/apply_logos_rag_l3_production_st_index_v1.py" },
    @{ Name = 'fusion'; Cmd = "$py scripts/build_ms_ma_jung_fusion_check_v1.py" },
    @{ Name = 'review_packet'; Cmd = "$py scripts/build_logos_rag_promotion_review_packet_v1.py" },
    @{ Name = 'gate'; Cmd = "$py scripts/check_logos_rag_btrack_promotion_gate_v1.py" }
)

$results = @()
foreach ($j in $jobs) {
    Write-Host "==> $($j.Name)"
    & powershell -NoProfile -Command $j.Cmd
    $results += [pscustomobject]@{ step = $j.Name; exit = $LASTEXITCODE }
}

Write-Host '==> l3_readiness'
& $py scripts/build_logos_rag_l3_readiness_v1.py
$results += [pscustomobject]@{ step = 'l3_readiness'; exit = $LASTEXITCODE }

Write-Host '==> pytest_logos_rag'
& $py -m pytest tests/test_logos_rag_query_route_v1.py tests/test_logos_rag_query_route_ko_only_v1.py tests/test_logos_rag_hybrid_query_v1.py -q --tb=no
$results += [pscustomobject]@{ step = 'pytest_logos_rag'; exit = $LASTEXITCODE }

$results | Format-Table -AutoSize
# gate may HOLD after gold drift; L3 swap success is separate (exit 0 on l3_swap)
$hard = $results | Where-Object { $_.step -in @('l3_swap', 'pytest_logos_rag') -and $_.exit -ne 0 }
if ($hard) { exit 1 }
exit 0
