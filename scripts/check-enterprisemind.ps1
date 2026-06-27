param()

$ErrorActionPreference = "Continue"
. "$PSScriptRoot\enterprisemind-common.ps1"

$root = Get-EnterpriseMindRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "EnterpriseMind environment check"
Write-Host "Project root: $root"

Write-Step "Project files"
if (Test-Path -LiteralPath (Join-Path $root "compose.dev.yml")) { Write-Ok "compose.dev.yml found" } else { Write-Fail "compose.dev.yml missing" }
if (Test-Path -LiteralPath (Join-Path $backend ".env")) { Write-Ok "backend\.env exists" } else { Write-Warn "backend\.env missing; start script can copy from .env.example" }
if (Test-Path -LiteralPath (Join-Path $frontend "node_modules")) { Write-Ok "frontend\node_modules exists" } else { Write-Warn "frontend\node_modules missing; run npm install" }

Write-Step "Command line tools"
if (Test-CommandExists "docker") { Write-Ok "docker command found" } else { Write-Fail "docker command missing" }
if (Test-CommandExists "conda") { Write-Ok "conda command found" } else { Write-Fail "conda command missing" }
if (Test-CondaEnv "em") { Write-Ok "conda env em found" } else { Write-Warn "conda env em not found or conda unavailable" }
if (Test-CommandExists "npm") { Write-Ok "npm command found" } else { Write-Warn "npm command missing" }
if (Test-CommandExists "ollama") { Write-Ok "ollama command found" } else { Write-Warn "ollama command missing" }

Write-Step "Docker"
if (Test-CommandExists "docker") {
    & docker version >$null 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Docker engine is reachable"
        Push-Location $root
        try {
            & docker compose -f compose.dev.yml ps
        } finally {
            Pop-Location
        }
    } else {
        Write-Warn "Docker engine is not reachable. Start Docker Desktop first."
    }
}

Write-Step "TCP ports"
$ports = @(
    @{ Name = "PostgreSQL"; Port = 5432 },
    @{ Name = "Redis"; Port = 6379 },
    @{ Name = "Qdrant"; Port = 6333 },
    @{ Name = "Backend API"; Port = 8000 },
    @{ Name = "Frontend Vite"; Port = 5173 },
    @{ Name = "Ollama"; Port = 11434 }
)
foreach ($item in $ports) {
    if (Test-TcpPort "127.0.0.1" $item.Port) {
        Write-Ok ("{0} port {1} open" -f $item.Name, $item.Port)
    } else {
        Write-Warn ("{0} port {1} not open" -f $item.Name, $item.Port)
    }
}

Write-Host ""
Write-Host "Check finished. This script does not call HTTP endpoints and does not print .env content."
