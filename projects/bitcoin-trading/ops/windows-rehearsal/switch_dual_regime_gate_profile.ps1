param(
    [ValidateSet("conservative", "balanced", "aggressive")]
    [string]$Profile = "balanced",
    [switch]$PersistUserEnv
)

$ErrorActionPreference = "Stop"

$name = "DUAL_REGIME_GATE_PROFILE"
$value = $Profile.ToLowerInvariant()

if ($PersistUserEnv) {
    [Environment]::SetEnvironmentVariable($name, $value, "User")
    Write-Host ("Set USER env {0}={1}" -f $name, $value)
}

Set-Item -Path ("Env:{0}" -f $name) -Value $value
Write-Host ("Set CURRENT SESSION env {0}={1}" -f $name, $value)

Write-Host "Recommended next step:"
Write-Host " - Restart daemon/watchdog process so runtime picks up the new gate profile."

