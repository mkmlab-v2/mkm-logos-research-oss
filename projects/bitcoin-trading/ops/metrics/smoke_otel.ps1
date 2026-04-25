$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$srcPath = Join-Path $projectRoot "src"

if (-not (Test-Path $srcPath)) {
    Write-Error "Missing src path: $srcPath"
    exit 1
}

if (-not $env:MKM_OTEL_ENABLED) { $env:MKM_OTEL_ENABLED = "1" }
if (-not $env:MKM_OTEL_CONSOLE) { $env:MKM_OTEL_CONSOLE = "1" }

$endpoint = $env:OTEL_EXPORTER_OTLP_TRACES_ENDPOINT
if ([string]::IsNullOrWhiteSpace($endpoint)) { $endpoint = $env:OTEL_EXPORTER_OTLP_ENDPOINT }
if ([string]::IsNullOrWhiteSpace($endpoint)) {
    Write-Host "[otel-smoke] OTLP endpoint not set; console exporter path will be used."
} else {
    Write-Host "[otel-smoke] OTLP endpoint: $endpoint"
}

$script = @'
import os
import sys
from pathlib import Path

project_root = Path(r"""__PROJECT_ROOT__""")
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.monitoring.trading_otel import init_otel_if_enabled, span

init_otel_if_enabled("mkm-otel-smoke")
with span("smoke.span", {"source": "powershell", "otel_enabled": os.getenv("MKM_OTEL_ENABLED", "")}):
    pass
print("otel_smoke_ok")
'@
$script = $script.Replace("__PROJECT_ROOT__", $projectRoot)

$tmpPy = Join-Path $env:TEMP "mkm_otel_smoke.py"
Set-Content -Path $tmpPy -Value $script -Encoding UTF8
py -3 $tmpPy
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
