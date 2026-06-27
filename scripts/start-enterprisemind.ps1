param(
    [switch]$SkipDocker,
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$StartWorker,
    [switch]$InstallFrontendDependencies
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\enterprisemind-common.ps1"

$root = Get-EnterpriseMindRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "EnterpriseMind one-click start"
Write-Host "Project root: $root"

Push-Location $root
try {
    Write-Step "Docker services"
    if (-not $SkipDocker) {
        if (-not (Test-CommandExists "docker")) {
            throw "docker command not found. Install Docker Desktop first."
        }
        & docker version >$null 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Docker engine is not reachable. Start Docker Desktop first."
        }
        & docker compose -f compose.dev.yml up -d
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose up failed."
        }
        Write-Ok "PostgreSQL, Redis and Qdrant compose services requested"
    } else {
        Write-Warn "Skipped Docker compose startup"
    }

    Write-Step "Conda env"
    if (Test-CondaEnv "em") {
        Write-Ok "conda env em found"
    } else {
        Write-Warn "conda env em not found. Create it before starting backend."
    }
    Write-Host "If you open a new shell manually, run: conda activate em"

    Write-Step "backend .env"
    $envFile = Join-Path $backend ".env"
    $envExample = Join-Path $backend ".env.example"
    if (Test-Path -LiteralPath $envFile) {
        Write-Ok "backend\.env exists; not overwritten"
    } elseif (Test-Path -LiteralPath $envExample) {
        Copy-Item -LiteralPath $envExample -Destination $envFile
        Write-Ok "backend\.env created from backend\.env.example"
        Write-Warn "Please edit backend\.env if you need real external model credentials"
    } else {
        Write-Warn "backend\.env.example missing; cannot create backend\.env"
    }

    Write-Step "Backend dependency smoke check"
    if (Test-CondaEnv "em") {
        Push-Location $backend
        try {
            & conda run -n em python -c "import fastapi, uvicorn, sqlalchemy, qdrant_client, redis, rq; print('backend deps ok')"
            if ($LASTEXITCODE -ne 0) {
                Write-Warn "Backend dependency smoke check failed. Reinstall backend dependencies in conda env em."
            } else {
                Write-Ok "Backend dependencies look available"
            }
        } finally {
            Pop-Location
        }
    }

    Write-Step "Frontend dependencies"
    $nodeModules = Join-Path $frontend "node_modules"
    if (Test-Path -LiteralPath $nodeModules) {
        Write-Ok "frontend\node_modules exists"
    } elseif ($InstallFrontendDependencies) {
        Push-Location $frontend
        try {
            & npm install
            if ($LASTEXITCODE -ne 0) {
                throw "npm install failed."
            }
            Write-Ok "npm install finished"
        } finally {
            Pop-Location
        }
    } else {
        Write-Warn "frontend\node_modules missing. Run npm install, or rerun with -InstallFrontendDependencies."
    }

    $backendQuoted = ConvertTo-PowerShellSingleQuoted $backend
    $frontendQuoted = ConvertTo-PowerShellSingleQuoted $frontend

    if (-not $SkipBackend) {
        Write-Step "Start backend FastAPI"
        $backendCommand = "`$Host.UI.RawUI.WindowTitle = 'EnterpriseMind Backend'; Set-Location -LiteralPath $backendQuoted; conda activate em; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
        Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand)
        Write-Ok "Backend window opened"
    }

    if ($StartWorker) {
        Write-Step "Start document ingestion worker"
        $workerCommand = "`$Host.UI.RawUI.WindowTitle = 'EnterpriseMind Worker'; Set-Location -LiteralPath $backendQuoted; conda activate em; python -m rq worker document_ingestion --url redis://127.0.0.1:6379/0 --worker-class rq.worker.SpawnWorker --with-scheduler"
        Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $workerCommand)
        Write-Ok "Worker window opened"
    }

    if (-not $SkipFrontend) {
        Write-Step "Start frontend Vite"
        if (Test-Path -LiteralPath $nodeModules) {
            $frontendCommand = "`$Host.UI.RawUI.WindowTitle = 'EnterpriseMind Frontend'; Set-Location -LiteralPath $frontendQuoted; npm run dev"
            Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand)
            Write-Ok "Frontend window opened"
        } else {
            Write-Warn "Frontend not started because node_modules is missing"
        }
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Open these URLs after services finish booting:"
Write-Host "  Backend API: http://127.0.0.1:8000"
Write-Host "  Swagger:     http://127.0.0.1:8000/docs"
Write-Host "  Frontend:    http://127.0.0.1:5173"
Show-DefaultAccounts

Write-Host ""
Write-Host "Common issues:"
Write-Host "  Docker Desktop not started; ports 5432/6333/6379/8000/5173 occupied."
Write-Host "  conda env em missing; frontend node_modules missing."
Write-Host "  Ollama not running, or models bge-m3 / qwen2.5:3b not pulled."
Write-Host "  Without DeepSeek API key, external calls use demo provider or cannot call a real external model."
Write-Host "  First-time setup still needs alembic upgrade head and seed scripts; this start script does not reset data."
