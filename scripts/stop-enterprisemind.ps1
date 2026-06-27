param(
    [switch]$DockerOnly,
    [switch]$KeepDocker
)

$ErrorActionPreference = "Continue"
. "$PSScriptRoot\enterprisemind-common.ps1"

$root = Get-EnterpriseMindRoot

Write-Host "EnterpriseMind stop"
Write-Host "Project root: $root"

if (-not $DockerOnly) {
    Write-Step "Stop dev PowerShell windows opened by start script"
    $titles = @(
        "EnterpriseMind Backend",
        "EnterpriseMind Frontend",
        "EnterpriseMind Worker"
    )
    $stopped = 0
    foreach ($process in Get-Process -Name "powershell" -ErrorAction SilentlyContinue) {
        foreach ($title in $titles) {
            if ($process.MainWindowTitle -like "$title*") {
                Stop-Process -Id $process.Id -Force
                $stopped += 1
                break
            }
        }
    }
    if ($stopped -gt 0) {
        Write-Ok "Stopped $stopped EnterpriseMind dev window(s)"
    } else {
        Write-Warn "No EnterpriseMind dev windows found. Close manual backend/frontend windows with Ctrl+C if needed."
    }
}

if (-not $KeepDocker) {
    Write-Step "Stop Docker compose services"
    if (Test-CommandExists "docker") {
        Push-Location $root
        try {
            & docker compose -f compose.dev.yml stop
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "Docker services stopped without removing volumes"
            } else {
                Write-Warn "docker compose stop failed. Is Docker Desktop running?"
            }
        } finally {
            Pop-Location
        }
    } else {
        Write-Warn "docker command not found"
    }
}

Write-Host ""
Write-Host "Stop script never removes database, Redis or Qdrant volumes."
