# Start Next dev simulating clinic.no1kmedi.com — localhost → /clinician (한의사 모드).
# Usage (from projects/no1kmedi): powershell -File scripts/dev-no1kmedi-portal.ps1
$ErrorActionPreference = "Stop"
$env:MKM_DEV_SIMULATE_NO1KMEDI_CLINIC = "1"
$env:MKM_DEV_SIMULATE_NO1KMEDI_APEX = ""
$env:MKM_DEV_SIMULATE_NO1KMEDI_HOST = ""
$port = if ($env:PORT) { $env:PORT } else { "3011" }
Write-Host "MKM_DEV_SIMULATE_NO1KMEDI_CLINIC=1 — open http://localhost:${port}/ (redirects to /clinician)"
npx next dev -p $port
