param(
    [switch]$RecycleExisting
)

$ErrorActionPreference = "SilentlyContinue"

$workspace = "C:\workspace"
$pythonLauncher = "C:\WINDOWS\py.exe"
if (-not (Test-Path -LiteralPath $pythonLauncher)) {
    $pythonLauncher = "py"
}

$logDir = Join-Path $workspace "reports\local_py_server_logs"
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$servers = @(
    @{
        Name = "bio_feedback_8787"
        Match = "run_bio_multilens_feedback_webhook_server_v1\.py"
        ScriptPath = Join-Path $workspace "scripts\run_bio_multilens_feedback_webhook_server_v1.py"
        Args = @("scripts/run_bio_multilens_feedback_webhook_server_v1.py", "--host", "127.0.0.1", "--port", "8787")
        OutLog = Join-Path $logDir "bio_feedback_8787_stdout.log"
        ErrLog = Join-Path $logDir "bio_feedback_8787_stderr.log"
    },
    @{
        Name = "compression_stub_8010"
        Match = "compression_token_api_stub:app"
        Args = @("-m", "uvicorn", "scripts.compression_token_api_stub:app", "--host", "127.0.0.1", "--port", "8010")
        OutLog = Join-Path $logDir "compression_stub_8010_stdout.log"
        ErrLog = Join-Path $logDir "compression_stub_8010_stderr.log"
    }
)

function Get-MatchingProcs([string]$pattern) {
    @(Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            ($_.Name -match '^(py|python)(\.exe)?$') -and
            ($_.CommandLine -match $pattern)
        })
}

foreach ($svc in $servers) {
    if ($svc.ContainsKey("ScriptPath") -and -not (Test-Path -LiteralPath $svc.ScriptPath)) {
        continue
    }

    $procs = Get-MatchingProcs -pattern $svc.Match

    if ($RecycleExisting -and $procs.Count -gt 0) {
        foreach ($p in $procs) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 400
        $procs = @()
    }

    if ($procs.Count -eq 0) {
        Start-Process -FilePath $pythonLauncher `
            -ArgumentList $svc.Args `
            -WindowStyle Hidden `
            -WorkingDirectory $workspace `
            -RedirectStandardOutput $svc.OutLog `
            -RedirectStandardError $svc.ErrLog | Out-Null
    }
}
