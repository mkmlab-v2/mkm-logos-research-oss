param(
    [int]$MinLifetimeSeconds = 8
)

$ErrorActionPreference = "SilentlyContinue"

$now = Get-Date
$killed = @()

$pyProcs = Get-CimInstance Win32_Process -Filter "Name='py.exe'"
foreach ($p in $pyProcs) {
    $cmd = if ($p.CommandLine) { $p.CommandLine.Trim() } else { "" }

    # "빈 창"은 보통 인자가 전혀 없는 py 런처로 뜬다. (서버/스크립트 실행은 Args가 붙는다)
    $isBlankCmd =
        [string]::IsNullOrWhiteSpace($cmd) -or
        ($cmd -imatch '^(?:")?C:\\Windows\\py\.exe(?:")?\s*$') -or
        ($cmd -imatch '^(?i)py(\.exe)?\s*$')

    if (-not $isBlankCmd) {
        continue
    }

    $created = $null
    try { $created = [System.Management.ManagementDateTimeConverter]::ToDateTime($p.CreationDate) } catch {}
    if ($created) {
        $age = ($now - $created).TotalSeconds
        if ($age -lt $MinLifetimeSeconds) {
            continue
        }
    }

    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    $killed += $p.ProcessId
}

if ($killed.Count -gt 0) {
    Write-Output ("killed_blank_py_pids=" + ($killed -join ","))
}
