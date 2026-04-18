$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$runner = Join-Path $projectRoot "ops\windows-rehearsal\collect_kpi_snapshot.py"
$canaryRunner = Join-Path $projectRoot "ops\windows-rehearsal\run_ops_local_llm_canary_gate.ps1"
$taskLog = Join-Path $projectRoot "memory\kpi\kpi_snapshot_task.log"

function Write-TaskLog([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Add-Content -Path $taskLog -Value $line
}

$maint = [System.Environment]::GetEnvironmentVariable("MKM_WORKSPACE_MAINTENANCE")
if ($maint -and ($maint.Trim().ToLower() -in @("1", "true", "yes", "on"))) {
    Write-TaskLog "SKIP: MKM_WORKSPACE_MAINTENANCE active (no KPI / canary writes)"
    exit 0
}

if (-not (Test-Path $runner)) {
    Write-TaskLog "ERROR runner missing: $runner"
    throw "KPI runner not found: $runner"
}

try {
    Set-Location $projectRoot
    $pythonExe = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonExe = "py"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonExe = "python"
    } elseif (Test-Path "C:\Python311\python.exe") {
        $pythonExe = "C:\Python311\python.exe"
    }

    if (-not $pythonExe) {
        Write-TaskLog "ERROR python runtime not found"
        throw "Python runtime not found (py/python/C:\\Python311\\python.exe)"
    }

    $stdoutFile = Join-Path $projectRoot "memory\kpi\kpi_snapshot_task.stdout.log"
    $stderrFile = Join-Path $projectRoot "memory\kpi\kpi_snapshot_task.stderr.log"
    $proc = Start-Process -FilePath $pythonExe -ArgumentList @("$runner") -WorkingDirectory $projectRoot -NoNewWindow -PassThru -Wait -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
    if ($proc.ExitCode -ne 0) {
        $stderrTail = ""
        if (Test-Path $stderrFile) {
            $stderrTail = (Get-Content $stderrFile -Tail 20 -ErrorAction SilentlyContinue) -join " | "
        }
        Write-TaskLog "ERROR runner exit code: $($proc.ExitCode); stderr_tail=$stderrTail"
        throw "KPI snapshot failed with exit code: $($proc.ExitCode)"
    }

    # Optional: run local-LLM canary gate after KPI snapshot.
    # Default ON; set OPS_LOCAL_LLM_CANARY_GATE_ON_KPI=0 to disable.
    $runCanary = $true
    $canaryFlag = [System.Environment]::GetEnvironmentVariable("OPS_LOCAL_LLM_CANARY_GATE_ON_KPI")
    if ($canaryFlag -and ($canaryFlag.Trim().ToLower() -in @("0", "false", "off", "no"))) {
        $runCanary = $false
    }
    if ($runCanary -and (Test-Path $canaryRunner)) {
        try {
            $canaryStdout = Join-Path $projectRoot "memory\kpi\ops_local_llm_canary_gate_on_kpi.stdout.log"
            $canaryStderr = Join-Path $projectRoot "memory\kpi\ops_local_llm_canary_gate_on_kpi.stderr.log"
            $canaryProc = Start-Process -FilePath "powershell" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $canaryRunner) -WorkingDirectory $projectRoot -NoNewWindow -PassThru -Wait -RedirectStandardOutput $canaryStdout -RedirectStandardError $canaryStderr
            if ($canaryProc.ExitCode -ne 0) {
                Write-TaskLog "WARN canary gate on KPI failed: exit=$($canaryProc.ExitCode)"
            } else {
                Write-TaskLog "OK canary gate on KPI success"
            }
        } catch {
            Write-TaskLog "WARN canary gate on KPI exception: $($_.Exception.Message)"
        }
    }

    Write-TaskLog "OK runner success via $pythonExe"
    exit 0
} catch {
    Write-TaskLog "ERROR exception: $($_.Exception.Message)"
    exit 1
}
