#Requires -Version 5.1
<#
.SYNOPSIS
  Capture plain TUI bench output for README demo / vhs recording.

.EXAMPLE
  powershell -File scripts\Invoke-MkmBenchTuiDemoCapture_v1.ps1
#>
param(
    [string]$OutTxt = "docs/final/artifacts/mkm_bench_tui_demo_transcript_v1.txt",
    [string]$OutJson = "reports/mkm_bench_tui_demo_capture_v1_latest.json"
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) { $py = "python" }

$proc = Start-Process -FilePath $py -ArgumentList @(
    "scripts/run_mkm_bench_tui_spike_v1.py", "--replay-only", "--plain"
) -NoNewWindow -Wait -PassThru -RedirectStandardOutput ([System.IO.Path]::GetFullPath($OutTxt)) -RedirectStandardError "NUL"

if ($proc.ExitCode -ne 0) {
    throw "bench TUI capture failed exit $($proc.ExitCode)"
}

$doc = @{
    schema           = "mkm_bench_tui_demo_capture_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    ok               = $true
    exit_code        = 0
    transcript_path  = $OutTxt
    reproduce        = "powershell -File scripts/Invoke-MkmBenchTuiDemoCapture_v1.ps1"
    vhs_hint         = "Optional: vhs record docs/final/artifacts/mkm_bench_tui_demo_v1.tape"
}
$outJsonPath = Join-Path (Get-Location) $OutJson
$json = $doc | ConvertTo-Json -Depth 4
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($outJsonPath, $json + "`n", $utf8NoBom)

Write-Host "OK: $OutTxt" -ForegroundColor Green
Write-Host "OK: $OutJson" -ForegroundColor Green
